from ekg.schemas import Edge, Entity, Graph


def relation_valid(relation: str, head_type: str, tail_type: str, ontology: dict[str, object]) -> bool:
    relations = ontology.get("relations", {})
    if not isinstance(relations, dict) or relation not in relations:
        return False
    spec = relations[relation]
    if not isinstance(spec, dict):
        return False
    domain = spec.get("domain", [])
    ranges = spec.get("range", [])
    if not isinstance(domain, list) or not isinstance(ranges, list):
        return False
    return (head_type in domain or "same" in domain) and (tail_type in ranges or "same" in ranges)


def validate_graph(entities: list[Entity], edges: list[Edge], ontology: dict[str, object]) -> Graph:
    entity_map = {entity.id: entity for entity in entities}
    merged: dict[tuple[str, str, str], Edge] = {}
    for edge in edges:
        head, tail = entity_map.get(edge.head_id), entity_map.get(edge.tail_id)
        if head is None or tail is None or head.id == tail.id or not relation_valid(edge.relation, head.type, tail.type, ontology):
            continue
        key = (edge.head_id, edge.relation, edge.tail_id)
        existing = merged.get(key)
        if existing is None:
            merged[key] = edge
        else:
            merged[key] = existing.model_copy(update={"evidence": sorted(set(existing.evidence + edge.evidence)), "chunk_ids": sorted(set(existing.chunk_ids + edge.chunk_ids)), "confidence": max(existing.confidence, edge.confidence)})
    for edge in merged.values():
        opposite = "OPPOSES" if edge.relation == "ALLY_OF" else "ALLY_OF" if edge.relation == "OPPOSES" else ""
        if opposite and (edge.head_id, opposite, edge.tail_id) in merged:
            merged[(edge.head_id, edge.relation, edge.tail_id)] = edge.model_copy(update={"contradictory": True})
    return Graph(entities=entities, edges=list(merged.values()))
