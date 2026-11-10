from ekg.schemas import Edge, Entity, Graph


class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase
        self.driver = GraphDatabase.driver(uri, auth=(user, password), connection_timeout=30.0)

    def save(self, graph_id: str, graph: Graph) -> None:
        from neo4j.exceptions import Neo4jError

        try:
            with self.driver.session() as session:
                session.run("CREATE CONSTRAINT entity_graph_id_id IF NOT EXISTS FOR (n:Entity) REQUIRE (n.graph_id, n.id) IS UNIQUE").consume()
                for entity in graph.entities:
                    session.run("MERGE (n:Entity {graph_id: $graph_id, id: $id}) SET n.name = $name, n.type = $type, n.aliases = $aliases, n.context = $context", graph_id=graph_id, id=entity.id, name=entity.name, type=entity.type, aliases=entity.aliases, context=entity.context).consume()
                for edge in graph.edges:
                    session.run("MATCH (a:Entity {graph_id: $graph_id, id: $head}), (b:Entity {graph_id: $graph_id, id: $tail}) MERGE (a)-[r:RELATES {graph_id: $graph_id, type: $relation}]->(b) SET r.evidence = $evidence, r.chunk_ids = $chunks, r.confidence = $confidence, r.contradictory = $contradictory", graph_id=graph_id, head=edge.head_id, tail=edge.tail_id, relation=edge.relation, evidence=edge.evidence, chunks=edge.chunk_ids, confidence=edge.confidence, contradictory=edge.contradictory).consume()
        except Neo4jError as exc:
            raise RuntimeError("Neo4j write failed") from exc

    def get_graph(self, graph_id: str) -> Graph:
        from neo4j.exceptions import Neo4jError

        try:
            with self.driver.session() as session:
                entity_rows = session.run("MATCH (n:Entity {graph_id: $graph_id}) RETURN n.id AS id, n.name AS name, n.type AS type, n.aliases AS aliases, n.context AS context", graph_id=graph_id).data()
                edge_rows = session.run("MATCH (a:Entity {graph_id: $graph_id})-[r:RELATES {graph_id: $graph_id}]->(b:Entity {graph_id: $graph_id}) RETURN a.id AS head_id, r.type AS relation, b.id AS tail_id, r.evidence AS evidence, r.chunk_ids AS chunk_ids, r.confidence AS confidence, r.contradictory AS contradictory", graph_id=graph_id).data()
            entities = [Entity(id=str(row["id"]), name=str(row["name"]), type=str(row["type"]), aliases=list(row["aliases"] or []), context=row["context"]) for row in entity_rows]
            edges = [Edge(head_id=str(row["head_id"]), relation=str(row["relation"]), tail_id=str(row["tail_id"]), evidence=list(row["evidence"] or []), chunk_ids=list(row["chunk_ids"] or []), confidence=float(row["confidence"]), contradictory=bool(row["contradictory"])) for row in edge_rows]
            return Graph(entities=entities, edges=edges)
        except Neo4jError as exc:
            raise RuntimeError("Neo4j read failed") from exc
