from ekg.llm.base import LLMClient
from ekg.resolve.adjudicate import adjudicate
from ekg.resolve.blocking import block_key
from ekg.resolve.scoring import score_entities
from ekg.schemas import Edge, Entity


def resolve_entities(entities: list[Entity], edges: list[Edge], high: float, low: float, client: LLMClient | None = None) -> tuple[list[Entity], list[Edge]]:
    parents = list(range(len(entities)))

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[parents[value]]
            value = parents[value]
        return value

    def union(left: int, right: int) -> None:
        parents[find(right)] = find(left)

    buckets: dict[tuple[str, str, str | None], list[int]] = {}
    for index, entity in enumerate(entities):
        buckets.setdefault(block_key(entity), []).append(index)
    for indexes in buckets.values():
        for offset, left_index in enumerate(indexes):
            for right_index in indexes[offset + 1:]:
                left, right = entities[left_index], entities[right_index]
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
        output.append(first.model_copy(update={"id": identifier, "aliases": aliases}))
        replacements.update({entities[index].id: identifier for index in group})
    return output, [edge.model_copy(update={"head_id": replacements[edge.head_id], "tail_id": replacements[edge.tail_id]}) for edge in edges]
