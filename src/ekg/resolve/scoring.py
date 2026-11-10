from rapidfuzz.fuzz import ratio

from ekg.normalize.aliases import normalize_name
from ekg.schemas import Entity


def score_entities(left: Entity, right: Entity) -> float:
    return ratio(normalize_name(left.name), normalize_name(right.name)) / 100
