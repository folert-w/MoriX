from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import DB_PATH
from .logger import get_logger

log = get_logger(__name__)


def _connect() -> sqlite3.Connection:
    """Создаёт подключение к SQLite с row_factory=Row."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Создаёт таблицы, если их ещё нет. Можно вызывать много раз."""
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            conv_id     INTEGER NOT NULL,
            role        TEXT NOT NULL,  -- 'user', 'assistant', 'system'
            text        TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (conv_id) REFERENCES conversations(id) ON DELETE CASCADE
        );
        """
    )

    conn.commit()
    conn.close()
    log.info("DB initialized at %s", DB_PATH)


# --------- Работа с диалогами ---------


def get_default_conversation() -> int:
    """
    Возвращает id существующего "дефолтного" диалога
    или создаёт новый, если ничего нет.
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM conversations ORDER BY created_at ASC LIMIT 1;"
    )
    row = cur.fetchone()
    if row:
        conv_id = int(row["id"])
        conn.close()
        return conv_id

    cur.execute(
        "INSERT INTO conversations (title) VALUES (?);",
        ("Мой первый диалог",),
    )
    conv_id = cur.lastrowid
    conn.commit()
    conn.close()
    log.info("Created default conversation id=%s", conv_id)
    return int(conv_id)


def create_conversation(title: str) -> int:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (title) VALUES (?);",
        (title,),
    )
    conv_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(conv_id)


def list_conversations(limit: int = 50) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, title, created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
        LIMIT ?;
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --------- Работа с сообщениями ---------


def add_message(conv_id: int, role: str, text: str) -> int:
    """
    Сохраняет сообщение в БД и обновляет updated_at у диалога.
    role: 'user' | 'assistant' | 'system'
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO messages (conv_id, role, text)
        VALUES (?, ?, ?);
        """,
        (conv_id, role, text),
    )
    msg_id = cur.lastrowid

    cur.execute(
        "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?;",
        (conv_id,),
    )

    conn.commit()
    conn.close()
    return int(msg_id)


def get_messages(conv_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()

    if limit is None:
        cur.execute(
            """
            SELECT id, role, text, created_at
            FROM messages
            WHERE conv_id = ?
            ORDER BY id ASC;
            """,
            (conv_id,),
        )
    else:
        cur.execute(
            """
            SELECT id, role, text, created_at
            FROM messages
            WHERE conv_id = ?
            ORDER BY id DESC
            LIMIT ?;
            """,
            (conv_id, limit),
        )

    rows = cur.fetchall()
    conn.close()

    # если limit был, мы брали с конца, разворачиваем обратно по времени
    if limit is not None:
        rows = rows[::-1]

    return [dict(r) for r in rows]

def rename_conversation(conv_id: int, new_title: str) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE conversations SET title = ?, updated_at = datetime('now') WHERE id = ?;",
        (new_title, conv_id),
    )
    conn.commit()
    conn.close()


def delete_conversation(conv_id: int) -> None:
    conn = _connect()
    cur = conn.cursor()
    # сначала сообщения (если вдруг нет CASCADE)
    cur.execute("DELETE FROM messages WHERE conv_id = ?;", (conv_id,))
    # потом сам диалог
    cur.execute("DELETE FROM conversations WHERE id = ?;", (conv_id,))
    conn.commit()
    conn.close()


def clear_messages(conv_id: int) -> None:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE conv_id = ?;", (conv_id,))
    cur.execute(
        "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?;",
        (conv_id,),
    )
    conn.commit()
    conn.close()

