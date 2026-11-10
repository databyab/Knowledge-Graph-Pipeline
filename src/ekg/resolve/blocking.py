from ekg.normalize.aliases import normalize_name
from ekg.schemas import Entity


def block_key(entity: Entity) -> tuple[str, str, str | None]:
    token = normalize_name(entity.name).split(" ")[0]
    return entity.type, token, entity.context
