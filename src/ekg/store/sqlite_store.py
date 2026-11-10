import json
import sqlite3
import threading
from pathlib import Path

from ekg.schemas import Graph


class SQLiteStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        self.connection.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, config_hash TEXT, provider TEXT, model TEXT, metrics TEXT)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, graph TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS shares (id TEXT PRIMARY KEY, graph_id TEXT NOT NULL)")
        self.connection.commit()

    def save_graph(self, graph_id: str, graph: Graph) -> None:
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO snapshots(id, graph) VALUES (?, ?)", (graph_id, graph.model_dump_json()))
            self.connection.commit()

    def get_graph(self, graph_id: str) -> Graph | None:
        with self.lock:
            row = self.connection.execute("SELECT graph FROM snapshots WHERE id = ?", (graph_id,)).fetchone()
        return Graph.model_validate_json(row[0]) if row else None

    def save_run(self, run_id: str, config_hash: str, provider: str, model: str, metrics: dict[str, float]) -> None:
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?)", (run_id, config_hash, provider, model, json.dumps(metrics)))
            self.connection.commit()

    def save_share(self, share_id: str, graph_id: str) -> None:
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO shares VALUES (?, ?)", (share_id, graph_id))
            self.connection.commit()

    def graph_for_share(self, share_id: str) -> Graph | None:
        with self.lock:
            row = self.connection.execute("SELECT graph_id FROM shares WHERE id = ?", (share_id,)).fetchone()
        return self.get_graph(str(row[0])) if row else None
