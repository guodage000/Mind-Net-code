import sqlite3
from app.core.config import settings


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表和 FTS5 全文索引"""
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                content     TEXT NOT NULL DEFAULT '',
                tags        TEXT NOT NULL DEFAULT '[]',
                status      TEXT,
                priority    TEXT,
                deadline    TEXT,
                parent_id   TEXT,
                note_type   TEXT DEFAULT 'note',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                id UNINDEXED,
                title,
                content,
                tags,
                tokenize = 'unicode61'
            );

            CREATE TABLE IF NOT EXISTS links (
                source_id   TEXT NOT NULL,
                target_id   TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id)
            );

            CREATE TABLE IF NOT EXISTS tags (
                name        TEXT PRIMARY KEY,
                count       INTEGER DEFAULT 0
            );
        """)
        conn.commit()
    finally:
        conn.close()
