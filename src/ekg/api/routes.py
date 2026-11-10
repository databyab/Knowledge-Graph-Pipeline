import logging
import secrets
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from ekg.api.security import IpRateLimiter, require_api_key, require_write_rate
from ekg.extract.extractor import ExtractionError
from ekg.schemas import Graph
from ekg.settings import EnvSettings, load_yaml
from ekg.store.sqlite_store import SQLiteStore

LOGGER = logging.getLogger(__name__)


class GraphRequest(BaseModel):
    text: str = Field(min_length=1)
    context: str | None = None
    entity_config: dict[str, object] | None = None


class GraphService:
    def __init__(self, settings: EnvSettings, store: SQLiteStore, builder: Callable[[str, str, str | None, dict[str, object] | None], Graph], max_jobs: int = 4) -> None:
        self.settings, self.store, self.builder = settings, store, builder
        self.statuses: dict[str, str] = {}
        self.shares: dict[str, str] = {}
        self.limiter = IpRateLimiter()
        self.jobs = threading.BoundedSemaphore(max_jobs)

    def run(self, graph_id: str, request: GraphRequest) -> None:
        if not self.jobs.acquire(blocking=False):
            self.statuses[graph_id] = "rejected"
            return
        self.statuses[graph_id] = "running"
        try:
            graph = self.builder(graph_id, request.text, request.context, request.entity_config)
            self.store.save_graph(graph_id, graph)
            share_id = secrets.token_urlsafe(16)
            self.store.save_share(share_id, graph_id)
            self.shares[graph_id] = share_id
            self.statuses[graph_id] = "completed"
        except ExtractionError as exc:
            LOGGER.error(
                "graph build failed: ExtractionError reason=%s raw_triples=%d dropped=%s finish_reason=%s truncated=%s",
                exc.reason,
                exc.raw_triples,
                exc.dropped,
                exc.finish_reason,
                exc.truncated,
            )
            self.statuses[graph_id] = "failed"
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            LOGGER.error("graph build failed: %s", type(exc).__name__)
            self.statuses[graph_id] = "failed"
        finally:
            self.jobs.release()


def create_router(service: GraphService, root: Path, config: dict[str, object]) -> APIRouter:
    router = APIRouter()
    expected_key = service.settings.api_key.get_secret_value()
    limit = int(config["request_body_limit"])
    max_chars = int(config["max_input_chars"])

    @router.post("/v1/graphs", status_code=202)
    async def create_graph(request: Request, background: BackgroundTasks) -> JSONResponse:
        require_api_key(request, expected_key)
        require_write_rate(request, service.limiter)
        body = await request.body()
        if len(body) > limit:
            raise HTTPException(status_code=413, detail="request too large")
        data = GraphRequest.model_validate_json(body)
        if len(data.text) > max_chars:
            raise HTTPException(status_code=413, detail="input too large")
        graph_id = str(uuid.uuid4())
        service.statuses[graph_id] = "queued"
        background.add_task(service.run, graph_id, data)
        return JSONResponse({"id": graph_id}, status_code=202)

    @router.get("/v1/graphs/{graph_id}")
    async def get_graph(graph_id: str, request: Request) -> dict[str, object]:
        require_api_key(request, expected_key)
        graph = service.store.get_graph(graph_id)
        return {"id": graph_id, "status": service.statuses.get(graph_id, "not_found"), "graph": graph.model_dump() if graph else None, "share_id": service.shares.get(graph_id)}

    @router.get("/")
    async def build_page() -> FileResponse:
        return FileResponse(root / "web" / "viewer" / "build.html", headers={"Content-Security-Policy": "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; connect-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none'", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})

    @router.get("/g/{share_id}")
    async def viewer(share_id: str) -> FileResponse:
        if service.store.graph_for_share(share_id) is None:
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(root / "web" / "viewer" / "index.html", headers={"Content-Security-Policy": "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; connect-src 'self' https://cdn.jsdelivr.net; frame-ancestors 'none'", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})

    @router.get("/v1/share/{share_id}")
    async def share_data(share_id: str) -> dict[str, object]:
        graph = service.store.graph_for_share(share_id)
        if graph is None:
            raise HTTPException(status_code=404, detail="not found")
        return graph.model_dump()

    @router.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return router
