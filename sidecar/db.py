"""
Camada de banco do Transcreve (SQLite, stdlib).

Mantém uma única fonte de verdade local para projetos, áudios, transcrições,
codificação qualitativa e cache de análises. O esquema é versionado por
`PRAGMA user_version`, permitindo migrações incrementais sem perder dados.

Decisões:
- `sqlite3` puro (sem ORM) — domínio pequeno, controle total e zero dependências.
- Conexão por thread (FastAPI roda handlers em threads); SQLite em modo WAL para
  leituras concorrentes. Chaves estrangeiras com ON DELETE CASCADE ligadas.
- `segments.words` guardado como JSON (timestamps por palavra), evitando uma
  tabela enorme; consultas analíticas usam o texto/segmentos, não cada palavra.
"""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from paths import db_path

# Versão atual do esquema. Incrementar a cada migração em `_MIGRATIONS`.
SCHEMA_VERSION = 1

# DDL inicial (v1). Em produção, alterações futuras entram como passos de migração.
_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    path        TEXT    NOT NULL,
    filename    TEXT    NOT NULL,
    duration    REAL,
    language    TEXT,
    model       TEXT,
    device      TEXT,
    status      TEXT    NOT NULL DEFAULT 'pending',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audios_project ON audios(project_id);

CREATE TABLE IF NOT EXISTS segments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_id  INTEGER NOT NULL REFERENCES audios(id) ON DELETE CASCADE,
    seq       INTEGER NOT NULL,
    start     REAL    NOT NULL,
    "end"     REAL    NOT NULL,
    text      TEXT    NOT NULL,
    speaker   TEXT,
    words     TEXT
);
CREATE INDEX IF NOT EXISTS idx_segments_audio ON segments(audio_id, seq);

CREATE TABLE IF NOT EXISTS codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    color       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(project_id, name)
);
CREATE INDEX IF NOT EXISTS idx_codes_project ON codes(project_id);

CREATE TABLE IF NOT EXISTS segment_codes (
    segment_id INTEGER NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    code_id    INTEGER NOT NULL REFERENCES codes(id) ON DELETE CASCADE,
    memo       TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (segment_id, code_id)
);

CREATE TABLE IF NOT EXISTS analyses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    audio_id    INTEGER REFERENCES audios(id) ON DELETE CASCADE,
    kind        TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_analyses_scope ON analyses(project_id, audio_id, kind);
"""

# Passos de migração: índice i aplica a versão (i+1). Vazio por ora (estamos na v1).
_MIGRATIONS: list[str] = []

# Uma conexão por thread — sqlite3.Connection não deve cruzar threads.
_local = threading.local()


def _new_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_connection() -> sqlite3.Connection:
    """Conexão SQLite reutilizada por thread (FastAPI usa um pool de threads)."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _new_connection()
        _local.conn = conn
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """
    Contexto transacional: commit no sucesso, rollback em exceção.

        with transaction() as conn:
            conn.execute(...)
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    """
    Cria o esquema na primeira execução e aplica migrações pendentes.

    Idempotente: seguro chamar a cada boot do sidecar.
    """
    conn = get_connection()
    version = conn.execute("PRAGMA user_version").fetchone()[0]

    if version == 0:
        conn.executescript(_SCHEMA_V1)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
        return

    # Aplica migrações incrementais (da versão atual até a SCHEMA_VERSION).
    for v in range(version, SCHEMA_VERSION):
        conn.executescript(_MIGRATIONS[v - 1])
        conn.execute(f"PRAGMA user_version = {v + 1}")
        conn.commit()
