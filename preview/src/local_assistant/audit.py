from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
import sqlite3
from datetime import datetime, timezone


class AuditStore:
    def __init__(self, data_dir: Path):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "assistant.db"
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def _managed_connection(self) -> Iterator[sqlite3.Connection]:
        """Commit or roll back and always release the database file handle.

        sqlite3.Connection's own context manager does not close the connection.
        That is easy to miss on POSIX, where an open file may still be unlinked,
        but it leaves assistant.db locked on Windows.
        """
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _init(self) -> None:
        with self._managed_connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS file_moves (
                    operation_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    status TEXT NOT NULL,
                    PRIMARY KEY (operation_id, ordinal),
                    FOREIGN KEY (operation_id) REFERENCES operations(id)
                );
                """
            )

    def begin(self, operation_id: str, fingerprint: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._managed_connection() as connection:
            connection.execute(
                "INSERT INTO operations VALUES (?, ?, 'file_move', 'running', ?)",
                (operation_id, now, fingerprint),
            )

    def record_move(self, operation_id: str, ordinal: int, source: Path, destination: Path) -> None:
        with self._managed_connection() as connection:
            connection.execute(
                "INSERT INTO file_moves VALUES (?, ?, ?, ?, 'moved')",
                (operation_id, ordinal, str(source), str(destination)),
            )

    def finish(self, operation_id: str, status: str = "completed") -> None:
        with self._managed_connection() as connection:
            connection.execute("UPDATE operations SET status=? WHERE id=?", (status, operation_id))

    def moves_for(self, operation_id: str) -> list[tuple[str, str, str]]:
        with self._managed_connection() as connection:
            rows = connection.execute(
                "SELECT source, destination, status FROM file_moves WHERE operation_id=? ORDER BY ordinal DESC",
                (operation_id,),
            ).fetchall()
        return [(str(a), str(b), str(c)) for a, b, c in rows]

    def mark_undone(self, operation_id: str) -> None:
        with self._managed_connection() as connection:
            connection.execute("UPDATE operations SET status='undone' WHERE id=?", (operation_id,))
            connection.execute("UPDATE file_moves SET status='undone' WHERE operation_id=?", (operation_id,))
