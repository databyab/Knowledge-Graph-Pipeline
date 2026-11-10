from pathlib import Path

from fastapi.testclient import TestClient

from ekg.api.routes import GraphRequest, GraphService, create_router
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
