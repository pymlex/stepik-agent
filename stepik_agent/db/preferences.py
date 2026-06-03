import sqlite3
from pathlib import Path


class PreferencesStore:
    """Persistent user preferences across sessions."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.commit()

    def set_preference(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO preferences (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        self._conn.commit()

    def get_preference(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def list_preferences(self) -> dict[str, str]:
        rows = self._conn.execute("SELECT key, value FROM preferences").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def add_session_note(self, note: str) -> None:
        self._conn.execute(
            "INSERT INTO session_notes (note) VALUES (?)", (note,)
        )
        self._conn.commit()

    def recent_notes(self, limit: int = 10) -> list[str]:
        rows = self._conn.execute(
            "SELECT note FROM session_notes ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [row["note"] for row in rows]

    def close(self) -> None:
        self._conn.close()
