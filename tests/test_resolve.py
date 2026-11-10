import logging

from ekg.resolve.cluster import resolve_entities
from ekg.schemas import Entity


def test_resolve_merges_same_type_and_context() -> None:
    entities = [Entity(id="1", name="A", type="Person", context="x"), Entity(id="2", name="a", type="Person", context="x")]
    output, _ = resolve_entities(entities, [], 0.8, 0.5)
    assert len(output) == 1


def test_identical_normalized_names_merge_across_types_and_keep_majority(caplog) -> None:
    entities = [
        Entity(id="1", name="Eko Prime", type="Person", context="universe-a"),
        Entity(id="2", name="eko prime", type="Organization", context="universe-a"),
        Entity(id="3", name="EKO PRIME", type="Organization", context="universe-a"),
        Entity(id="4", name="Eko Prime", type="Concept", context="universe-b"),
    ]
    with caplog.at_level(logging.INFO, logger="ekg.resolve.cluster"):
        output, _ = resolve_entities(entities, [], 0.9, 0.6)
    assert len(output) == 2
    merged = next(entity for entity in output if entity.context == "universe-a")
    assert merged.type == "Organization"
    assert {"eko prime", "EKO PRIME"} <= set(merged.aliases)
    assert "exact_name_merges=2" in caplog.text


def test_identical_name_type_tie_keeps_first_seen_type() -> None:
    entities = [
        Entity(id="1", name="Rill Delta", type="Person"),
        Entity(id="2", name="Rill Delta", type="Organization"),
    ]
    output, _ = resolve_entities(entities, [], 0.9, 0.6)
    assert len(output) == 1
    assert output[0].type == "Person"
