from ekg.normalize.aliases import normalize_name
from ekg.schemas import Entity


def block_key(entity: Entity) -> tuple[str, str, str | None]:
    token = normalize_name(entity.name).split(" ")[0]
    return entity.type, token, entity.context


def exact_name_key(entity: Entity) -> tuple[str, str | None]:
    return normalize_name(entity.name), entity.context


def entity_name_keys(entity: Entity) -> set[tuple[str, str | None]]:
    return {
        (normalized, entity.context)
        for value in [entity.name, *entity.aliases]
        if (normalized := normalize_name(value))
    }
