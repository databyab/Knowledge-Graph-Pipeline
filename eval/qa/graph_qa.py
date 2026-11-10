QUERIES = {
    "neighbors": "MATCH (a:Entity {id: $entity_id})-[r:RELATES]->(b:Entity) RETURN b.id AS id, r.type AS type",
    "two_hop": "MATCH (a:Entity {id: $entity_id})-[r1:RELATES]->()-[r2:RELATES]->(b:Entity) RETURN b.id AS id, r1.type AS first_type, r2.type AS second_type",
    "shortest_path": "MATCH p=shortestPath((a:Entity {id: $from_id})-[*..5]-(b:Entity {id: $to_id})) RETURN [node IN nodes(p) | node.id] AS ids",
}
