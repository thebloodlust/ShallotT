"""
Translation memory cache for ShallotT.
Stores (source_text, src_lang, target_lang, model) → translation
in a local SQLite database for instant recall.
"""

import sqlite3
import hashlib
import json
import os
import threading
from src.config import CONFIG_DIR

DB_PATH = os.path.join(CONFIG_DIR, "translation_cache.db")
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS cache (
            text_hash TEXT NOT NULL,
            src_lang  TEXT NOT NULL,
            tgt_lang  TEXT NOT NULL,
            model     TEXT NOT NULL,
            translation TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (text_hash, src_lang, tgt_lang, model)
        )"""
    )
    conn.commit()
    return conn


def _make_hash(text: str, src_lang: str, target_lang: str, model: str) -> str:
    """Deterministic hash for (text + language pair + model)."""
    payload = f"{text.strip()}|{src_lang}|{target_lang}|{model}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def lookup(text: str, src_lang: str, target_lang: str, model: str) -> str | None:
    """Return cached translation or None."""
    with _lock:
        conn = _get_conn()
        h = _make_hash(text, src_lang, target_lang, model)
        row = conn.execute(
            "SELECT translation FROM cache WHERE text_hash = ?",
            (h,)
        ).fetchone()
        conn.close()
    return row[0] if row else None


def store(text: str, src_lang: str, target_lang: str, model: str, translation: str):
    """Save a translation to the cache."""
    with _lock:
        conn = _get_conn()
        h = _make_hash(text, src_lang, target_lang, model)
        conn.execute(
            "INSERT OR REPLACE INTO cache (text_hash, src_lang, tgt_lang, model, translation) "
            "VALUES (?, ?, ?, ?, ?)",
            (h, src_lang, target_lang, model, translation)
        )
        conn.commit()
        conn.close()


def stats() -> dict:
    """Return cache statistics."""
    with _lock:
        conn = _get_conn()
        count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        conn.close()
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
    return {"entries": count, "size_mb": round(size_mb, 2)}


def get_recent(limit: int = 50, search: str = "") -> list[dict]:
    """Return recent translations, optionally filtered by search text."""
    with _lock:
        conn = _get_conn()
        if search:
            rows = conn.execute(
                "SELECT text_hash, src_lang, tgt_lang, model, translation, created_at "
                "FROM cache WHERE translation LIKE ? OR text_hash IN "
                "(SELECT text_hash FROM cache GROUP BY text_hash HAVING "
                "SUM(CASE WHEN translation LIKE ? THEN 1 ELSE 0 END) > 0) "
                "ORDER BY created_at DESC LIMIT ?",
                (f"%{search}%", f"%{search}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT text_hash, src_lang, tgt_lang, model, translation, created_at "
                "FROM cache ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
    return [
        {
            "source_lang": r[1], "target_lang": r[2], "model": r[3],
            "translation": r[4], "created_at": r[5],
        }
        for r in rows
    ]


def get_source_text(hash_val: str) -> str:
    """Retrieve the original source text for a cached translation (best-effort)."""
    return ""  # Source text is not stored separately; hash is one-way


def clear():
    """Delete all cached translations."""
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM cache")
        conn.commit()
        conn.close()
