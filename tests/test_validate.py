from ekg.schemas import Edge, Entity
from ekg.validate.checks import validate_graph


def test_validate_marks_contradiction_and_merges_duplicates() -> None:
    entities = [Entity(id="a", name="A", type="Person"), Entity(id="b", name="B", type="Person")]
    edges = [Edge(head_id="a", relation="ALLY_OF", tail_id="b", evidence=["one"], confidence=0.2), Edge(head_id="a", relation="OPPOSES", tail_id="b", evidence=["two"], confidence=0.9)]
    graph = validate_graph(entities, edges, {"relations": {"ALLY_OF": {"domain": ["Person"], "range": ["Person"]}, "OPPOSES": {"domain": ["Person"], "range": ["Person"]}}})
    assert all(edge.contradictory for edge in graph.edges)
