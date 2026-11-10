from pathlib import Path
from typing import Any

from ekg.schemas import Edge, Entity, Graph
from ekg.store.neo4j_store import Neo4jStore
from ekg.store.sqlite_store import SQLiteStore


class FakeResult:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or []

    def consume(self) -> None:
        return None

    def data(self) -> list[dict[str, object]]:
        return self.rows


class FakeSession:
    def __init__(self, driver: "FakeDriver") -> None:
        self.driver = driver

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def run(self, query: str, **parameters: Any) -> FakeResult:
        self.driver.queries.append((query, parameters))
        if query.startswith("CREATE CONSTRAINT"):
            return FakeResult()
        if query.startswith("MERGE (n:Entity"):
            self.driver.nodes[(str(parameters["graph_id"]), str(parameters["id"]))] = dict(parameters)
            return FakeResult()
        if query.startswith("MATCH (a:Entity") and "MERGE (a)-" in query:
            self.driver.edges.append(dict(parameters))
            return FakeResult()
        graph_id = str(parameters["graph_id"])
        if "RETURN n.id AS id" in query:
            return FakeResult([{"id": node["id"], "name": node["name"], "type": node["type"], "aliases": node["aliases"], "context": node["context"]} for (node_graph_id, _), node in self.driver.nodes.items() if node_graph_id == graph_id])
        return FakeResult([{"head_id": edge["head"], "relation": edge["relation"], "tail_id": edge["tail"], "evidence": edge["evidence"], "chunk_ids": edge["chunks"], "confidence": edge["confidence"], "contradictory": edge["contradictory"]} for edge in self.driver.edges if str(edge["graph_id"]) == graph_id])


class FakeDriver:
    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str], dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.queries: list[tuple[str, dict[str, Any]]] = []

    def session(self) -> FakeSession:
        return FakeSession(self)


def test_sqlite_store_round_trip(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "store.db")
    graph = Graph(entities=[Entity(id="<hostile>", name="<hostile>", type="Person")], edges=[])
    store.save_graph("graph", graph)
    assert store.get_graph("graph") == graph


def test_neo4j_graphs_are_scoped_by_graph_id() -> None:
    driver = FakeDriver()
    store = Neo4jStore.__new__(Neo4jStore)
    store.driver = driver
    graph_one = Graph(entities=[Entity(id="entity", name="Shared", type="Person"), Entity(id="one", name="One", type="Organization")], edges=[Edge(head_id="entity", relation="MEMBER_OF", tail_id="one", evidence=["one"], chunk_ids=["one"], confidence=0.9)])
    graph_two = Graph(entities=[Entity(id="entity", name="Shared", type="Person"), Entity(id="two", name="Two", type="Organization")], edges=[Edge(head_id="entity", relation="MEMBER_OF", tail_id="two", evidence=["two"], chunk_ids=["two"], confidence=0.9)])
    store.save("build-one", graph_one)
    store.save("build-two", graph_two)
    assert store.get_graph("build-one") == graph_one
    assert store.get_graph("build-two") == graph_two
    entity_queries = [query for query, _ in driver.queries if query.startswith("MERGE (n:Entity")]
    edge_queries = [query for query, _ in driver.queries if "MERGE (a)-" in query]
    assert all("graph_id" in query for query in entity_queries + edge_queries)
