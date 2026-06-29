"""
Repositório do Transcreve — operações de domínio sobre o SQLite.

Camada fina entre a API (FastAPI) e o banco (`db.py`). Centraliza as consultas e
mantém os handlers HTTP enxutos. Retorna dicts (serializáveis direto em JSON);
os modelos Pydantic da API descrevem o contrato externo.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from db import get_connection, transaction


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _rows(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


# --- Projetos ------------------------------------------------------------


def create_project(name: str, description: str | None = None) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description),
        )
        return get_project(cur.lastrowid)  # type: ignore[return-value]


def list_projects() -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY updated_at DESC, id DESC"
    ).fetchall()
    return _rows(rows)


def get_project(project_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    return _row(
        conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    )


def update_project(
    project_id: int, name: str | None = None, description: str | None = None
) -> dict[str, Any] | None:
    sets, params = [], []
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if description is not None:
        sets.append("description = ?")
        params.append(description)
    if sets:
        sets.append("updated_at = datetime('now')")
        params.append(project_id)
        with transaction() as conn:
            conn.execute(
                f"UPDATE projects SET {', '.join(sets)} WHERE id = ?", params
            )
    return get_project(project_id)


def delete_project(project_id: int) -> bool:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        return cur.rowcount > 0


# --- Áudios --------------------------------------------------------------


def create_audio(
    project_id: int,
    path: str,
    filename: str,
    *,
    duration: float | None = None,
    language: str | None = None,
    model: str | None = None,
    device: str | None = None,
    status: str = "pending",
) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO audios
                (project_id, path, filename, duration, language, model, device, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (project_id, path, filename, duration, language, model, device, status),
        )
        return get_audio(cur.lastrowid)  # type: ignore[return-value]


def list_audios(project_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM audios WHERE project_id = ? ORDER BY created_at DESC, id DESC",
        (project_id,),
    ).fetchall()
    return _rows(rows)


def get_audio(audio_id: int) -> dict[str, Any] | None:
    conn = get_connection()
    return _row(
        conn.execute("SELECT * FROM audios WHERE id = ?", (audio_id,)).fetchone()
    )


def update_audio_status(
    audio_id: int,
    status: str,
    *,
    duration: float | None = None,
    language: str | None = None,
    model: str | None = None,
    device: str | None = None,
) -> dict[str, Any] | None:
    sets = ["status = ?", "updated_at = datetime('now')"]
    params: list[Any] = [status]
    for col, val in (
        ("duration", duration),
        ("language", language),
        ("model", model),
        ("device", device),
    ):
        if val is not None:
            sets.append(f"{col} = ?")
            params.append(val)
    params.append(audio_id)
    with transaction() as conn:
        conn.execute(f"UPDATE audios SET {', '.join(sets)} WHERE id = ?", params)
    return get_audio(audio_id)


def delete_audio(audio_id: int) -> bool:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM audios WHERE id = ?", (audio_id,))
        return cur.rowcount > 0


# --- Segmentos (transcrição) --------------------------------------------


def replace_segments(audio_id: int, segments: list[dict[str, Any]]) -> int:
    """
    Substitui todos os segmentos de um áudio (idempotente por retranscrição).

    Cada item: {seq, start, end, text, speaker?, words?}. `words` é uma lista
    (timestamps por palavra) serializada como JSON.
    """
    with transaction() as conn:
        conn.execute("DELETE FROM segments WHERE audio_id = ?", (audio_id,))
        conn.executemany(
            """
            INSERT INTO segments (audio_id, seq, start, "end", text, speaker, words)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    audio_id,
                    s["seq"],
                    s["start"],
                    s["end"],
                    s["text"],
                    s.get("speaker"),
                    json.dumps(s["words"], ensure_ascii=False)
                    if s.get("words")
                    else None,
                )
                for s in segments
            ],
        )
        return len(segments)


def list_segments(audio_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM segments WHERE audio_id = ? ORDER BY seq', (audio_id,)
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["words"] = json.loads(d["words"]) if d["words"] else []
        out.append(d)
    return out


# --- Códigos / codificação qualitativa ----------------------------------


def create_code(
    project_id: int, name: str, color: str | None = None
) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO codes (project_id, name, color) VALUES (?, ?, ?)",
            (project_id, name, color),
        )
        row = conn.execute(
            "SELECT * FROM codes WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def list_codes(project_id: int) -> list[dict[str, Any]]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM codes WHERE project_id = ? ORDER BY name", (project_id,)
    ).fetchall()
    return _rows(rows)


def delete_code(code_id: int) -> bool:
    with transaction() as conn:
        cur = conn.execute("DELETE FROM codes WHERE id = ?", (code_id,))
        return cur.rowcount > 0


def assign_code(segment_id: int, code_id: int, memo: str | None = None) -> None:
    """Vincula um código a um segmento (upsert do memo se já existir)."""
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO segment_codes (segment_id, code_id, memo)
            VALUES (?, ?, ?)
            ON CONFLICT(segment_id, code_id) DO UPDATE SET memo = excluded.memo
            """,
            (segment_id, code_id, memo),
        )


def unassign_code(segment_id: int, code_id: int) -> bool:
    with transaction() as conn:
        cur = conn.execute(
            "DELETE FROM segment_codes WHERE segment_id = ? AND code_id = ?",
            (segment_id, code_id),
        )
        return cur.rowcount > 0


def segments_for_code(code_id: int) -> list[dict[str, Any]]:
    """Trechos marcados com um código (para revisão temática)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.*, sc.memo
        FROM segment_codes sc
        JOIN segments s ON s.id = sc.segment_id
        WHERE sc.code_id = ?
        ORDER BY s.audio_id, s.seq
        """,
        (code_id,),
    ).fetchall()
    return _rows(rows)


# --- Análises (cache) ----------------------------------------------------


def save_analysis(
    kind: str,
    payload: dict[str, Any],
    *,
    project_id: int | None = None,
    audio_id: int | None = None,
) -> dict[str, Any]:
    with transaction() as conn:
        cur = conn.execute(
            "INSERT INTO analyses (project_id, audio_id, kind, payload) VALUES (?, ?, ?, ?)",
            (project_id, audio_id, kind, json.dumps(payload, ensure_ascii=False)),
        )
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d


def latest_analysis(
    kind: str, *, project_id: int | None = None, audio_id: int | None = None
) -> dict[str, Any] | None:
    conn = get_connection()
    row = conn.execute(
        """
        SELECT * FROM analyses
        WHERE kind = ?
          AND (project_id IS ? OR ? IS NULL)
          AND (audio_id IS ? OR ? IS NULL)
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (kind, project_id, project_id, audio_id, audio_id),
    ).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d
