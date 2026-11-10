import logging
from pathlib import Path

from fastapi.testclient import TestClient

from ekg.api.routes import GraphRequest, GraphService, create_router
from ekg.extract.extractor import ExtractionError
from ekg.settings import EnvSettings
from ekg.store.sqlite_store import SQLiteStore


def test_graph_request_validates_text() -> None:
    request = GraphRequest(text="trusted text")
    assert request.text == "trusted text"


def test_router_is_created(tmp_path: Path) -> None:
    settings = EnvSettings(api_key="secret", groq_model="model", gemini_model="model")
    service = GraphService(settings, SQLiteStore(tmp_path / "db"), lambda graph_id, text, context, config: __import__("ekg.schemas", fromlist=["Graph"]).Graph())
    router = create_router(service, tmp_path, {"request_body_limit": 100, "max_input_chars": 50})
    assert {route.path for route in router.routes} >= {"/", "/v1/graphs", "/v1/graphs/{graph_id}", "/healthz"}


def test_root_has_csp_and_no_cookies() -> None:
    from ekg.api.main import create_app

    client = TestClient(create_app())
    for path in ("/", "/healthz"):
        response = client.get(path)
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert "set-cookie" not in response.headers


def test_graph_service_logs_safe_extraction_details(caplog, tmp_path: Path) -> None:
    def fail_build(graph_id: str, text: str, context: str | None, config: dict[str, object] | None):
        raise ExtractionError(
            "evidence_not_substring",
            3,
            {"schema_invalid": 0, "entity_name_invalid": 0, "evidence_not_substring": 1},
            "stop",
            False,
        )

    service = GraphService(
        EnvSettings(api_key="secret"), SQLiteStore(tmp_path / "db"), fail_build
    )
    with caplog.at_level(logging.ERROR, logger="ekg.api.routes"):
        service.run("graph-id", GraphRequest(text="private source"))
    assert service.statuses["graph-id"] == "failed"
    assert "reason=evidence_not_substring" in caplog.text
    assert "raw_triples=3" in caplog.text
    assert "private source" not in caplog.text
