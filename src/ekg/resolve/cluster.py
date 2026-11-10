import logging

from ekg.llm.base import LLMClient
from ekg.resolve.adjudicate import adjudicate
from ekg.resolve.blocking import block_key, entity_name_keys, exact_name_key
from ekg.resolve.scoring import score_entities
from ekg.schemas import Edge, Entity

LOGGER = logging.getLogger(__name__)


def resolve_entities(entities: list[Entity], edges: list[Edge], high: float, low: float, client: LLMClient | None = None) -> tuple[list[Entity], list[Edge]]:
    parents = list(range(len(entities)))

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left: int, right: int) -> None:
        parents[find(right)] = find(left)

    exact_groups: dict[tuple[str, str | None], list[int]] = {}
    for index, entity in enumerate(entities):
        exact_groups.setdefault(exact_name_key(entity), []).append(index)
    exact_name_merges = 0
    for indexes in exact_groups.values():
        for index in indexes[1:]:
            if find(indexes[0]) != find(index):
                union(indexes[0], index)
                exact_name_merges += 1
    alias_groups: dict[tuple[str, str | None], list[int]] = {}
    for index, entity in enumerate(entities):
        for key in entity_name_keys(entity):
            alias_groups.setdefault(key, []).append(index)
    for indexes in alias_groups.values():
        for index in indexes[1:]:
            if find(indexes[0]) != find(index):
                union(indexes[0], index)
    LOGGER.info("exact_name_merges=%d", exact_name_merges)

    buckets: dict[tuple[str, str, str | None], list[int]] = {}
    for index, entity in enumerate(entities):
        buckets.setdefault(block_key(entity), []).append(index)
    for indexes in buckets.values():
        for offset, left_index in enumerate(indexes):
            for right_index in indexes[offset + 1:]:
                left, right = entities[left_index], entities[right_index]
                if find(left_index) == find(right_index):
                    continue
                value = score_entities(left, right)
                same = value >= high or (low <= value < high and client is not None and adjudicate(client, left, right))
                if same and left.context == right.context:
                    union(left_index, right_index)
    groups: dict[int, list[int]] = {}
    for index in range(len(entities)):
        groups.setdefault(find(index), []).append(index)
    replacements: dict[str, str] = {}
    output: list[Entity] = []
    for group in groups.values():
        first = entities[group[0]]
        identifier = first.id
        aliases = sorted({alias for index in group for alias in [entities[index].name, *entities[index].aliases] if alias != first.name})
        type_counts = {entity_type: sum(entities[index].type == entity_type for index in group) for entity_type in {entities[index].type for index in group}}
        most_frequent_type = max(type_counts.values())
        chosen_type = next(entities[index].type for index in group if type_counts[entities[index].type] == most_frequent_type)
        output.append(first.model_copy(update={"id": identifier, "type": chosen_type, "aliases": aliases}))
        replacements.update({entities[index].id: identifier for index in group})
    return output, [edge.model_copy(update={"head_id": replacements[edge.head_id], "tail_id": replacements[edge.tail_id]}) for edge in edges]
