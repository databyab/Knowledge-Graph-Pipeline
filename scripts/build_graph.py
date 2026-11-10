import argparse
import logging
from pathlib import Path
from typing import cast

from ekg.llm.gemini_client import GeminiClient
from ekg.llm.groq_client import GroqClient
from ekg.llm.cache import ResponseCache
from ekg.llm.limiter import RateLimiter
from ekg.pipeline import build_graph
from ekg.settings import load_env_settings, load_yaml
from ekg.store.neo4j_store import Neo4jStore
from ekg.store.sqlite_store import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--entity-config", type=Path)
    parser.add_argument("--context")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = load_yaml(root / "config" / "pipeline.yaml")
    settings = load_env_settings()
    cache = ResponseCache(root / "responses.db")
    limiter = RateLimiter(int(config["rpm"]), int(config["tpm"]))
    provider = str(config["provider"])
    client = GroqClient(settings.groq_api_key.get_secret_value(), cast(str, settings.groq_model), cache, limiter, float(config["timeout_seconds"]), int(config["max_output_tokens"])) if provider == "groq" else GeminiClient(settings.gemini_api_key.get_secret_value(), cast(str, settings.gemini_model), cache, limiter, int(config["max_output_tokens"]))
    entity_config = load_yaml(args.entity_config) if args.entity_config else None
    neo4j = Neo4jStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password.get_secret_value())
    graph = build_graph(args.input.read_text(encoding="utf-8"), args.input.stem, args.context, client, root / "config", SQLiteStore(root / "graphs.db"), entity_config, neo4j)
    logging.info("built graph with %d entities and %d edges", len(graph.entities), len(graph.edges))


if __name__ == "__main__":
    main()
