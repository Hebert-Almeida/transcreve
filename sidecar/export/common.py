"""Blocos comuns aos exportadores: tipo de resultado, tempo e escrita tabular.

Mantém os exportadores concretos enxutos — todos produzem uma `Export` e
reaproveitam `rows_to_csv`/`rows_to_json` para os formatos tabulares.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from typing import Any, NamedTuple

# Media types por formato (servidos no Content-Type da resposta).
MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "tsv": "text/tab-separated-values; charset=utf-8",
    "json": "application/json; charset=utf-8",
    "srt": "application/x-subrip; charset=utf-8",
    "vtt": "text/vtt; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


class Export(NamedTuple):
    """Resultado de uma exportação, pronto para o handler HTTP servir."""

    content: bytes
    media_type: str
    filename: str


@dataclass(frozen=True)
class TableExport:
    """Tabela genérica (cabeçalho + linhas de dicts) para os formatos tabulares."""

    columns: list[str]
    rows: list[dict[str, Any]]


_SLUG_RE = re.compile(r"[^0-9A-Za-z._-]+")


def slugify(name: str) -> str:
    """Nome de arquivo seguro a partir de um título (sem extensão)."""
    slug = _SLUG_RE.sub("_", name.strip()).strip("_")
    return slug or "transcreve"


def srt_time(seconds: float) -> str:
    """Timestamp SRT: HH:MM:SS,mmm."""
    return _hms(seconds, ",")


def vtt_time(seconds: float) -> str:
    """Timestamp WebVTT: HH:MM:SS.mmm."""
    return _hms(seconds, ".")


def _hms(seconds: float, ms_sep: str) -> str:
    total_ms = max(0, round((seconds or 0.0) * 1000))
    ms = total_ms % 1000
    s = total_ms // 1000
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}{ms_sep}{ms:03d}"


def rows_to_csv(table: TableExport, *, delimiter: str = ",") -> bytes:
    """Serializa a tabela em CSV/TSV (UTF-8 com BOM para o Excel ler acentos)."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=table.columns, delimiter=delimiter, extrasaction="ignore"
    )
    writer.writeheader()
    writer.writerows(table.rows)
    return buf.getvalue().encode("utf-8-sig")


def rows_to_json(payload: Any) -> bytes:
    """Serializa qualquer estrutura como JSON UTF-8 indentado."""
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
