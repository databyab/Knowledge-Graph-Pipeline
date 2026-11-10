import hashlib
import sqlite3
import threading
from pathlib import Path


class ResponseCache:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.connection.execute("CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.connection.commit()

    @staticmethod
    def key(provider: str, model: str, prompt_version: str, system: str, user: str) -> str:
        value = "\x00".join((provider, model, prompt_version, system, user))
        return hashlib.sha256(value.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        with self.lock:
            row = self.connection.execute("SELECT value FROM responses WHERE key = ?", (key,)).fetchone()
        return str(row[0]) if row else None

    def put(self, key: str, value: str) -> None:
        with self.lock:
            self.connection.execute("INSERT OR REPLACE INTO responses(key, value) VALUES (?, ?)", (key, value))
            self.connection.commit()
