"""
Análise quantitativa: métricas descritivas da transcrição.

Trabalha sobre as tabelas `audios` e `segments` (texto + timestamps + falante).
Calcula contagem de palavras, velocidade de fala (palavras/min), riqueza lexical
(type-token ratio), termos mais frequentes e o recorte por falante — base para
relatório e exportação a outras ferramentas (ex.: RStudio). Sem pandas: tokenização
e contagens simples em Python, fiel ao estilo de `qualitative.py`.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from functools import lru_cache
from typing import Any

from db import get_connection

# "Stopwords" do português — descartadas na frequência de termos para destacar o
# vocabulário de conteúdo. Lista enxuta e pragmática (artigos, preposições,
# conjunções, pronomes e verbos de ligação comuns), não exaustiva.
_STOPWORDS_PT = frozenset(
    """
    a o e que de do da dos das em um uma uns umas no na nos nas ao aos as os
    por para com sem sob sobre entre ate até como mas se ou nem ja já quando
    onde quem qual quais cujo cuja muito muita mais menos tao tão tambem também
    so só ele ela eles elas eu tu voce você nos nós vos eles me te lhe nos vos
    meu minha seu sua dele dela este esta esse essa isso isto aquele aquela
    aquilo e é foi sao são era eram ser estar tem tem ter haver havia foi fui
    sera será nao não sim ha há vai vou vamos esta está estou estamos
    """.split()
)

_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÿ]+(?:[-'][0-9A-Za-zÀ-ÿ]+)*", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Palavras em minúsculas (mantém acentos), preservando hífens internos."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


@lru_cache(maxsize=None)
def _strip_accents(word: str) -> str:
    """Normaliza para comparar com a lista de stopwords (sem acento).

    Em cache: o mesmo punhado de palavras de função se repete milhares de vezes
    numa transcrição, então normaliza-se cada palavra distinta uma única vez.
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", word)
        if unicodedata.category(c) != "Mn"
    )


def _is_content_word(word: str) -> bool:
    """Palavra de conteúdo para a frequência de termos (sem stopwords, len > 1)."""
    return len(word) > 1 and _strip_accents(word) not in _STOPWORDS_PT


def _segment_rows(audio_id: int) -> list[Any]:
    conn = get_connection()
    return conn.execute(
        'SELECT text, speaker, start, "end" FROM segments '
        "WHERE audio_id = ? ORDER BY seq",
        (audio_id,),
    ).fetchall()


def _seconds(row: Any) -> float:
    """Duração não-negativa de um segmento."""
    return max(0.0, (row["end"] or 0.0) - (row["start"] or 0.0))


def _basic_metrics(tokens: list[str], seconds: float) -> dict[str, Any]:
    """Métricas descritivas a partir de uma lista de tokens e do tempo falado."""
    word_count = len(tokens)
    minutes = seconds / 60.0
    return {
        "word_count": word_count,
        "unique_words": len(set(tokens)),
        "spoken_seconds": round(seconds, 2),
        "speaking_rate": round(word_count / minutes, 1) if minutes > 0 else 0.0,
        # Type-token ratio: vocabulário distinto sobre total (riqueza lexical).
        "lexical_richness": round(len(set(tokens)) / word_count, 4)
        if word_count
        else 0.0,
    }


def _top_terms(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [
        {"term": term, "count": count} for term, count in counter.most_common(limit)
    ]


def audio_metrics(audio_id: int, *, top_terms: int = 25) -> dict[str, Any]:
    """
    Métricas descritivas de um áudio transcrito.

    Retorna contagem de palavras, tempo falado, velocidade (palavras/min),
    riqueza lexical (type-token ratio), termos mais frequentes (sem stopwords)
    e o recorte por falante. Vazio/seguro quando não há transcrição.
    """
    rows = _segment_rows(audio_id)

    all_tokens: list[str] = []
    spoken_seconds = 0.0
    # Acumuladores por falante: tokens e tempo.
    by_speaker_tokens: dict[str, list[str]] = {}
    by_speaker_time: dict[str, float] = {}

    for r in rows:
        tokens = _tokenize(r["text"])
        all_tokens.extend(tokens)
        dur = _seconds(r)
        spoken_seconds += dur

        speaker = r["speaker"] or ""
        by_speaker_tokens.setdefault(speaker, []).extend(tokens)
        by_speaker_time[speaker] = by_speaker_time.get(speaker, 0.0) + dur

    counter = Counter(t for t in all_tokens if _is_content_word(t))

    speakers: list[dict[str, Any]] = []
    for speaker, tokens in by_speaker_tokens.items():
        secs = by_speaker_time.get(speaker, 0.0)
        speakers.append(
            {
                "speaker": speaker or None,
                "word_count": len(tokens),
                "spoken_seconds": round(secs, 2),
                "speaking_rate": round(len(tokens) / (secs / 60.0), 1)
                if secs > 0
                else 0.0,
            }
        )
    # Mais falantes primeiro pelo tempo de fala (mais informativo num relatório).
    speakers.sort(key=lambda s: s["spoken_seconds"], reverse=True)
    # Só expõe o recorte por falante quando há diarização (mais de um falante real).
    has_speakers = len([s for s in speakers if s["speaker"]]) > 1

    return {
        **_basic_metrics(all_tokens, spoken_seconds),
        "top_terms": _top_terms(counter, top_terms),
        "speakers": speakers if has_speakers else [],
    }


def project_metrics(project_id: int, *, top_terms: int = 25) -> dict[str, Any]:
    """
    Agrega as métricas de todos os áudios transcritos do projeto.

    Os tokens são somados entre áudios para a riqueza lexical e os termos do
    projeto inteiro; cada áudio também aparece individualmente para comparação.
    """
    conn = get_connection()
    audios = conn.execute(
        "SELECT id, filename, duration FROM audios "
        "WHERE project_id = ? AND status = 'done' ORDER BY created_at, id",
        (project_id,),
    ).fetchall()

    per_audio: list[dict[str, Any]] = []
    total_tokens: list[str] = []
    total_seconds = 0.0
    project_counter: Counter[str] = Counter()

    for a in audios:
        tokens: list[str] = []
        seconds = 0.0
        for r in _segment_rows(a["id"]):
            tokens.extend(_tokenize(r["text"]))
            seconds += _seconds(r)

        total_tokens.extend(tokens)
        total_seconds += seconds
        project_counter.update(t for t in tokens if _is_content_word(t))

        per_audio.append(
            {
                "audio_id": a["id"],
                "filename": a["filename"],
                **_basic_metrics(tokens, seconds),
            }
        )

    return {
        **_basic_metrics(total_tokens, total_seconds),
        "top_terms": _top_terms(project_counter, top_terms),
        "audios": per_audio,
    }
