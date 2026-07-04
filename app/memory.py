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
            is_follow_up INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_phone ON messages(phone)")
    # Migração leve: adiciona coluna se não existir (bancos antigos)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
    if "is_follow_up" not in cols:
        conn.execute("ALTER TABLE messages ADD COLUMN is_follow_up INTEGER NOT NULL DEFAULT 0")
    return conn


def save_message(phone: str, role: str, content: str, is_follow_up: bool = False) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (phone, role, content, is_follow_up) VALUES (?, ?, ?, ?)",
            (phone, role, content, 1 if is_follow_up else 0),
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


def count_messages(phone: str) -> int:
    """Conta quantas mensagens (user + bot) esse lead já teve. Usado pra
    saber se é a primeira interação (dá tempo pra saudação chegar)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE phone = ?", (phone,)
        ).fetchone()
    return row[0] if row else 0


def get_stale_phones(minutes: int) -> list[str]:
    """Retorna phones onde:
    - Última mensagem do lead (role='user') foi há mais de `minutes` min
    - Bot ainda não enviou follow-up após essa última mensagem do lead
    """
    with _connect() as conn:
        # Fase 1: candidatos — leads cuja última mensagem 'user' é antiga
        rows = conn.execute(
            """
            SELECT phone, MAX(id) AS last_user_id
            FROM messages
            WHERE role = 'user'
            GROUP BY phone
            HAVING datetime(MAX(created_at)) <= datetime('now', ? || ' minutes')
            """,
            (f"-{minutes}",),
        ).fetchall()

        stale = []
        for phone, last_user_id in rows:
            # Fase 2: descarta os que já receberam follow-up depois dessa msg
            has_followup = conn.execute(
                """
                SELECT 1 FROM messages
                WHERE phone = ? AND id > ? AND role = 'assistant' AND is_follow_up = 1
                LIMIT 1
                """,
                (phone, last_user_id),
            ).fetchone()
            if not has_followup:
                stale.append(phone)
        return stale
