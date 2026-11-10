import json
from pathlib import Path

from ekg.extract.extractor import extract_triples, parse_json_response
from ekg.pipeline import build_graph
from ekg.schemas import Chunk
from ekg.store.sqlite_store import SQLiteStore


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses

    def complete(self, system: str, user: str) -> str:
        return self.responses.pop(0)


ONTOLOGY = {"relations": {"ALLY_OF": {"domain": ["Person"], "range": ["Person"]}}}


def test_extractor_retries_and_rejects_non_evidence() -> None:
    client = FakeClient(['[{"head":{"name":"A","type":"Person"},"relation":"ALLY_OF","tail":{"name":"B","type":"Person"},"evidence":"C allied with D","confidence":0.9}]', '[{"head":{"name":"A","type":"Person"},"relation":"ALLY_OF","tail":{"name":"B","type":"Person"},"evidence":"A allied with B","confidence":0.9}]'])
    chunk = Chunk(chunk_id="c", source_id="s", text="A allied with B", text_hash="h")
    assert extract_triples(client, chunk, ONTOLOGY, True, 1)[0].relation == "ALLY_OF"


def test_parser_accepts_json_code_fence() -> None:
    assert parse_json_response("```json\n[]\n```") == []


def test_extractor_accepts_subject_object_compatibility_shape() -> None:
    client = FakeClient(['[{"subject":"A","subject_type":"Person","relation":"ALLY_OF","object":"B","object_type":"Person","evidence":"A allied with B","confidence":0.9}]'])
    chunk = Chunk(chunk_id="c", source_id="s", text="A allied with B", text_hash="h")
    assert extract_triples(client, chunk, ONTOLOGY, True, 0)[0].head.name == "A"


def test_pipeline_accumulates_triples_from_three_chunks(tmp_path: Path) -> None:
    responses: list[str] = []
    sentences: list[str] = []
    for index in range(3):
        first_evidence = f"Person{index} joined Organization{index}"
        second_evidence = f"Person{index} joined Organization{index + 3}"
        sentence = " ".join([first_evidence, "and", second_evidence] + [f"token{index}_{item}" for item in range(84)]) + "."
        sentences.append(sentence)
        responses.append(json.dumps([
            {"head": {"name": f"Person{index}", "type": "Person"}, "relation": "MEMBER_OF", "tail": {"name": f"Organization{index}", "type": "Organization"}, "evidence": first_evidence, "confidence": 0.9},
            {"head": {"name": f"Person{index}", "type": "Person"}, "relation": "MEMBER_OF", "tail": {"name": f"Organization{index + 3}", "type": "Organization"}, "evidence": second_evidence, "confidence": 0.9},
        ]))
    graph = build_graph(" ".join(sentences), "source", None, FakeClient(responses), Path("config"), SQLiteStore(tmp_path / "store.db"))
    assert len(graph.edges) == 6
