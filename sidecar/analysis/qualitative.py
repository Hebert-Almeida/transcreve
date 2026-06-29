"""
Análise qualitativa: estatísticas da codificação temática.

Trabalha sobre as tabelas `codes` e `segment_codes` (preenchidas pela UI ao
marcar trechos). Calcula frequência de cada código, co-ocorrência (códigos que
aparecem no mesmo trecho) e cobertura — métricas inspiradas em NVivo/ATLAS.ti
para revisão e relatório. Não depende de pandas: contagens simples em SQL/Python.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from db import get_connection


def code_frequencies(project_id: int) -> list[dict[str, Any]]:
    """
    Cada código do projeto com quantos trechos recebeu e o total de palavras
    desses trechos (peso textual do tema). Ordenado do mais frequente ao menos.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.name,
            c.color,
            COUNT(sc.segment_id) AS segment_count,
            COALESCE(SUM(
                CASE WHEN s.text != '' THEN
                    LENGTH(s.text) - LENGTH(REPLACE(s.text, ' ', '')) + 1
                ELSE 0 END
            ), 0) AS word_count
        FROM codes c
        LEFT JOIN segment_codes sc ON sc.code_id = c.id
        LEFT JOIN segments s ON s.id = sc.segment_id
        WHERE c.project_id = ?
        GROUP BY c.id
        ORDER BY segment_count DESC, c.name
        """,
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def code_cooccurrence(project_id: int) -> list[dict[str, Any]]:
    """
    Pares de códigos que co-ocorrem no mesmo trecho, com a contagem.
    Base para um mapa de co-ocorrência (quais temas andam juntos).
    """
    conn = get_connection()
    # Para cada segmento, os códigos atribuídos (restritos ao projeto).
    rows = conn.execute(
        """
        SELECT sc.segment_id, sc.code_id
        FROM segment_codes sc
        JOIN codes c ON c.id = sc.code_id
        WHERE c.project_id = ?
        """,
        (project_id,),
    ).fetchall()

    by_segment: dict[int, list[int]] = {}
    for r in rows:
        by_segment.setdefault(r["segment_id"], []).append(r["code_id"])

    pairs: Counter[tuple[int, int]] = Counter()
    for code_ids in by_segment.values():
        for a, b in combinations(sorted(set(code_ids)), 2):
            pairs[(a, b)] += 1

    if not pairs:
        return []

    # Nomes dos códigos para a saída ser legível.
    names = {
        r["id"]: r["name"]
        for r in conn.execute(
            "SELECT id, name FROM codes WHERE project_id = ?", (project_id,)
        ).fetchall()
    }
    return [
        {
            "code_a": a,
            "code_b": b,
            "name_a": names.get(a, str(a)),
            "name_b": names.get(b, str(b)),
            "count": count,
        }
        for (a, b), count in pairs.most_common()
    ]


def qualitative_summary(project_id: int) -> dict[str, Any]:
    """Resumo da codificação do projeto: frequências, co-ocorrência e totais."""
    freqs = code_frequencies(project_id)
    cooc = code_cooccurrence(project_id)

    conn = get_connection()
    coded_segments = conn.execute(
        """
        SELECT COUNT(DISTINCT sc.segment_id)
        FROM segment_codes sc
        JOIN codes c ON c.id = sc.code_id
        WHERE c.project_id = ?
        """,
        (project_id,),
    ).fetchone()[0]
    total_segments = conn.execute(
        """
        SELECT COUNT(*)
        FROM segments s
        JOIN audios a ON a.id = s.audio_id
        WHERE a.project_id = ?
        """,
        (project_id,),
    ).fetchone()[0]

    coverage = (coded_segments / total_segments) if total_segments else 0.0
    return {
        "codes": freqs,
        "cooccurrence": cooc,
        "coded_segments": coded_segments,
        "total_segments": total_segments,
        "coverage": round(coverage, 4),
    }
