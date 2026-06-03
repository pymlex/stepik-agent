import json
import sqlite3
from pathlib import Path


class SearchLogStore:
    """Logs every Stepik search query and returned course ids."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS search_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                query TEXT NOT NULL,
                course_ids TEXT NOT NULL,
                stage TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def log_search(
        self,
        session_id: str,
        query: str,
        course_ids: list[int],
        stage: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO search_events (session_id, query, course_ids, stage)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, query, json.dumps(course_ids), stage),
        )
        self._conn.commit()

    def all_queries(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, session_id, query, course_ids, stage, created_at "
            "FROM search_events ORDER BY id"
        ).fetchall()
        return [dict(row) for row in rows]

    def queries_for_session(self, session_id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT query FROM search_events WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [row["query"] for row in rows]

    def close(self) -> None:
        self._conn.close()
