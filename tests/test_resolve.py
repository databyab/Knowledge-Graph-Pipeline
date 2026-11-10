from ekg.resolve.cluster import resolve_entities
from ekg.schemas import Entity


def test_resolve_merges_same_type_and_context() -> None:
    entities = [Entity(id="1", name="A", type="Person", context="x"), Entity(id="2", name="a", type="Person", context="x")]
    output, _ = resolve_entities(entities, [], 0.8, 0.5)
    assert len(output) == 1
