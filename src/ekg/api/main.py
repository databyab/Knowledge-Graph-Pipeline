from pathlib import Path
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ekg.api.routes import GraphService, create_router
from ekg.llm.cache import ResponseCache
from ekg.llm.gemini_client import GeminiClient
from ekg.llm.groq_client import GroqClient
from ekg.llm.limiter import RateLimiter
from ekg.pipeline import build_graph
from ekg.schemas import Graph
from ekg.settings import load_env_settings, load_yaml
from ekg.store.neo4j_store import Neo4jStore
from ekg.store.sqlite_store import SQLiteStore


def create_app() -> FastAPI:
    root = Path(__file__).resolve().parents[3]
    settings = load_env_settings()
    config = load_yaml(root / "config" / "pipeline.yaml")
    store = SQLiteStore(root / "graphs.db")
    neo4j = Neo4jStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password.get_secret_value())
    cache = ResponseCache(root / "responses.db")
    limiter = RateLimiter(int(config["rpm"]), int(config["tpm"]))
    provider = str(config["provider"])
    if provider == "groq":
        client = GroqClient(settings.groq_api_key.get_secret_value(), cast(str, settings.groq_model), cache, limiter, float(config["timeout_seconds"]), int(config["max_output_tokens"]))
    else:
        client = GeminiClient(settings.gemini_api_key.get_secret_value(), cast(str, settings.gemini_model), cache, limiter, int(config["max_output_tokens"]))

    def builder(graph_id: str, text: str, context: str | None, entity_config: dict[str, object] | None) -> Graph:
        return build_graph(text, graph_id, context, client, root / "config", store, entity_config, neo4j)

    service = GraphService(settings, store, builder)
    app = FastAPI()

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; connect-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none'"
        return response

    if settings.cors_origin_list:
        app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_methods=["GET", "POST"], allow_headers=["X-API-Key", "Content-Type"])
    app.include_router(create_router(service, root, config))
    app.mount("/", StaticFiles(directory=root / "web" / "viewer"), name="viewer-assets")
    return app


app = create_app()
