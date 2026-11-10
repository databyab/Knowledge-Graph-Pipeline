import json
from pathlib import Path

from ekg.extract.extractor import extract_triples, extract_triples_report, parse_json_response
from ekg.extract.prompts import PROMPT_VERSION, make_system
from ekg.pipeline import build_graph
from ekg.schemas import Chunk
from ekg.settings import load_yaml
from ekg.store.sqlite_store import SQLiteStore


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.invalidated: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        return self.responses.pop(0)

    def invalidate(self, system: str, user: str) -> None:
        self.invalidated.append((system, user))


ONTOLOGY = {"relations": {"ALLY_OF": {"domain": ["Person"], "range": ["Person"]}}}


def test_extractor_retries_and_rejects_non_evidence() -> None:
    client = FakeClient(['[{"head":{"name":"A","type":"Person"},"relation":"ALLY_OF","tail":{"name":"B","type":"Person"},"evidence":"C allied with D","confidence":0.9}]', '[{"head":{"name":"A","type":"Person"},"relation":"ALLY_OF","tail":{"name":"B","type":"Person"},"evidence":"A allied with B","confidence":0.9}]'])
    chunk = Chunk(chunk_id="c", source_id="s", text="A allied with B", text_hash="h")
    assert extract_triples(client, chunk, ONTOLOGY, True, 1)[0].relation == "ALLY_OF"


def test_extractor_retries_after_invalid_json() -> None:
    response = '[{"head":{"name":"A","type":"Person"},"relation":"ALLY_OF","tail":{"name":"B","type":"Person"},"evidence":"A allied with B","confidence":0.9}]'
    client = FakeClient(["not JSON", response])
    chunk = Chunk(chunk_id="c", source_id="s", text="A allied with B", text_hash="h")
    assert extract_triples(client, chunk, ONTOLOGY, True, 1)[0].relation == "ALLY_OF"
    assert client.responses == []
    assert len(client.invalidated) == 1


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


def test_same_as_and_entity_config_aliases_merge_before_resolution(tmp_path: Path) -> None:
    text = (
        "Nora Ridge, also known as Nor Ridge, knows Ellis Stone. "
        "Ellis Stone took the name Ellis Vale and knows Nor Ridge. "
        "Nora Ridge knows E Stone."
    )
    client = FakeClient([json.dumps([
        {"head": {"name": "Nora Ridge", "type": "Person", "same_as": ["Nor Ridge"]}, "relation": "KNOWS", "tail": {"name": "Ellis Stone", "type": "Person"}, "evidence": "Nora Ridge, also known as Nor Ridge, knows Ellis Stone", "confidence": 0.9},
        {"head": {"name": "Ellis Stone", "type": "Person", "same_as": ["Ellis Vale"]}, "relation": "KNOWS", "tail": {"name": "Nor Ridge", "type": "Person"}, "evidence": "Ellis Stone took the name Ellis Vale and knows Nor Ridge", "confidence": 0.9},
        {"head": {"name": "Nora Ridge", "type": "Person"}, "relation": "KNOWS", "tail": {"name": "E Stone", "type": "Person"}, "evidence": "Nora Ridge knows E Stone", "confidence": 0.9},
    ])])
    graph = build_graph(
        text,
        "aliases",
        None,
        client,
        Path("config"),
        SQLiteStore(tmp_path / "aliases.db"),
        {"aliases": {"E Stone": "Ellis Stone"}},
    )
    assert len(graph.entities) == 2
    nora = next(entity for entity in graph.entities if entity.name == "Nora Ridge")
    ellis = next(entity for entity in graph.entities if entity.name == "Ellis Stone")
    assert "Nor Ridge" in nora.aliases
    assert {"Ellis Vale", "E Stone"} <= set(ellis.aliases)


def test_invalid_entity_names_are_counted_and_rejected() -> None:
    triples = [
        {"head": {"name": "Good Person", "type": "Person"}, "relation": "ALLY_OF", "tail": {"name": "Valid Peer", "type": "Person"}, "evidence": "Good Person knows Valid Peer", "confidence": 0.9},
        {"head": {"name": "This is a very long name", "type": "Person"}, "relation": "ALLY_OF", "tail": {"name": "Valid Peer", "type": "Person"}, "evidence": "This is a very long name knows Valid Peer", "confidence": 0.9},
        {"head": {"name": "a Named Event", "type": "Event"}, "relation": "ALLY_OF", "tail": {"name": "Valid Peer", "type": "Person"}, "evidence": "a Named Event knows Valid Peer", "confidence": 0.9},
    ]
    chunk = Chunk(chunk_id="c", source_id="s", text="Good Person knows Valid Peer. This is a very long name knows Valid Peer. a Named Event knows Valid Peer.", text_hash="h")
    report = extract_triples_report(FakeClient([json.dumps(triples)]), chunk, ONTOLOGY, True, 0)
    assert len(report.triples) == 1
    assert report.dropped["entity_name_invalid"] == 2


def test_ontology_and_prompt_relation_guidance() -> None:
    ontology = load_yaml(Path("config/ontology.yaml"))
    relations = ontology["relations"]
    assert set(relations) == {
        "MEMBER_OF",
        "PART_OF",
        "LOCATED_IN",
        "CREATED",
        "OWNS",
        "PARTICIPATED_IN",
        "ALLY_OF",
        "OPPOSES",
        "FAMILY_OF",
        "MENTORED",
        "CAUSED",
        "PRECEDED",
        "ATTENDED",
        "LEADS",
        "KNOWS",
        "TRAVELLED_TO",
        "PARENT_OF",
    }
    assert {"ATTENDED", "LEADS", "KNOWS", "TRAVELLED_TO", "PARENT_OF"} <= set(relations)
    prompt = make_system(ontology)
    assert "CREATED applies only when the subject built or authored" in prompt
    assert "helping or assisting does not count" in prompt
    assert "raised or adopted" in prompt
    assert "studied at" in prompt
    assert "became ruler of" in prompt
    assert "same_as" in prompt
    assert PROMPT_VERSION == "v3"
