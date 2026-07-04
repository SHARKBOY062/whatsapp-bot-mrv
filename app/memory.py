import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "conversations.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone)")
    return conn


def save_message(phone: str, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (phone, role, content) VALUES (?, ?, ?)",
            (phone, role, content),
        )


def get_history(phone: str, limit: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM (
                SELECT role, content, id FROM messages
                WHERE phone = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (phone, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in rows]
