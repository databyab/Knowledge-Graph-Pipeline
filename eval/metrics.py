from collections.abc import Iterable


def f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def set_scores(predicted: set[str], gold: set[str]) -> tuple[float, float, float]:
    true = len(predicted & gold)
    precision = true / len(predicted) if predicted else 0.0
    recall = true / len(gold) if gold else 0.0
    return precision, recall, f1(precision, recall)


def entity_scores(predicted: Iterable[str], gold: Iterable[str]) -> tuple[float, float, float]:
    return set_scores(set(predicted), set(gold))


def triple_scores(predicted: Iterable[tuple[str, str, str]], gold: Iterable[tuple[str, str, str]], aliases: dict[str, str] | None = None) -> tuple[float, float, float]:
    mapping = aliases or {}
    canonical = lambda value: mapping.get(value, value)
    left = {(canonical(head), relation, canonical(tail)) for head, relation, tail in predicted}
    right = {(canonical(head), relation, canonical(tail)) for head, relation, tail in gold}
    return set_scores({str(item) for item in left}, {str(item) for item in right})


def er_pairwise_scores(predicted: set[tuple[str, str]], gold: set[tuple[str, str]]) -> tuple[float, float]:
    true = len(predicted & gold)
    return (true / len(predicted) if predicted else 0.0, true / len(gold) if gold else 0.0)
