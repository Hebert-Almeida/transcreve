"""Exportação dos resultados de análise (quantitativa e sentimento).

JSON devolve o payload da análise como está (fiel ao que a API serve). CSV/TSV
achatam a parte mais útil para o RStudio: na quantitativa, as métricas por áudio;
no sentimento, a linha do tempo trecho a trecho (uma linha por segmento).
"""
from __future__ import annotations

from typing import Any

import repository as repo

from .common import (
    MEDIA_TYPES,
    Export,
    TableExport,
    rows_to_csv,
    rows_to_json,
    slugify,
)

# Colunas das tabelas achatadas, por tipo de análise.
_QUANTITATIVE_COLUMNS = [
    "audio_id",
    "filename",
    "word_count",
    "unique_words",
    "spoken_seconds",
    "speaking_rate",
    "lexical_richness",
]
_SENTIMENT_COLUMNS = [
    "segment_id",
    "audio_id",
    "start",
    "label",
    "polarity",
    "text",
]


def _quantitative_table(payload: dict[str, Any]) -> TableExport:
    """Uma linha por áudio com as métricas descritivas."""
    return TableExport(_QUANTITATIVE_COLUMNS, list(payload.get("audios", [])))


def _sentiment_table(payload: dict[str, Any]) -> TableExport:
    """Uma linha por trecho da linha do tempo (rótulo + polaridade)."""
    return TableExport(_SENTIMENT_COLUMNS, list(payload.get("timeline", [])))


# kind -> (computa o payload, achata em tabela).
_KINDS = {
    "quantitative": _quantitative_table,
    "sentiment": _sentiment_table,
}


def _compute(kind: str, project_id: int) -> dict[str, Any]:
    """Calcula (ou reaproveita o cache) o payload da análise do projeto."""
    if kind == "quantitative":
        from analysis.quantitative import project_metrics

        return project_metrics(project_id)
    if kind == "sentiment":
        from analysis.sentiment import project_sentiment

        return project_sentiment(project_id)
    raise ValueError(f"Análise desconhecida: {kind}")


def export_analysis(kind: str, fmt: str, *, project_id: int) -> Export:
    """Exporta o resultado de uma análise de projeto em CSV/TSV/JSON.

    `kind`: quantitative | sentiment. `fmt`: csv | tsv | json. JSON traz o payload
    completo; CSV/TSV trazem a tabela achatada mais útil para o RStudio.
    """
    if kind not in _KINDS:
        raise ValueError(f"Análise desconhecida: {kind}")

    payload = _compute(kind, project_id)
    project = repo.get_project(project_id)
    title = project["name"] if project else f"projeto-{project_id}"
    base = f"{slugify(title)}-{kind}"

    if fmt == "json":
        content: bytes = rows_to_json(payload)
    elif fmt in ("csv", "tsv"):
        table = _KINDS[kind](payload)
        content = rows_to_csv(table, delimiter="\t" if fmt == "tsv" else ",")
    else:
        raise ValueError(f"Formato de exportação não suportado: {fmt}")

    return Export(content, MEDIA_TYPES[fmt], f"{base}.{fmt}")
