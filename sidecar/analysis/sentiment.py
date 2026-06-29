"""
Análise de sentimento PT-BR: polaridade dos trechos da transcrição.

Usa o pysentimiento (modelo BERTimbau ajustado para PT) para classificar cada
segmento em positivo/negativo/neutro, e agrega o resultado em uma distribuição do
projeto, um recorte por áudio e uma linha do tempo dos trechos (para localizar os
momentos mais marcados emocionalmente — útil em pesquisa qualitativa).

Diferente das análises quantitativa/qualitativa, a inferência é cara (uma passagem
de rede neural por trecho). Por isso o resultado é gravado em cache na tabela
`analyses`, com uma assinatura do conteúdo; só recalcula quando os segmentos mudam.
"""
from __future__ import annotations

from typing import Any

from db import get_connection

# Rótulos do pysentimiento → chaves estáveis usadas pela API/UI.
_LABELS = {"POS": "positive", "NEG": "negative", "NEU": "neutral"}

# Analisador carregado sob demanda (importa torch/transformers e baixa o modelo
# na primeira vez). Mantido em módulo para reaproveitar entre requisições.
_analyzer: Any = None


def _get_analyzer() -> Any:
    global _analyzer
    if _analyzer is None:
        from pysentimiento import create_analyzer

        _analyzer = create_analyzer(task="sentiment", lang="pt")
    return _analyzer


def _empty_distribution() -> dict[str, int]:
    return {"positive": 0, "negative": 0, "neutral": 0}


def _classify(texts: list[str]) -> list[dict[str, Any]]:
    """Classifica uma lista de textos: rótulo + probabilidades por trecho."""
    if not texts:
        return []
    analyzer = _get_analyzer()
    results = analyzer.predict(texts)  # aceita lista; uma passagem em lote
    out: list[dict[str, Any]] = []
    for r in results:
        out.append(
            {
                "label": _LABELS.get(r.output, "neutral"),
                "scores": {
                    _LABELS[k]: round(float(v), 4) for k, v in r.probas.items()
                },
            }
        )
    return out


def _signature(rows: list[Any]) -> str:
    """Assinatura do conteúdo: invalida o cache se os segmentos mudarem.

    Combina contagem e o maior id de segmento — `replace_segments` recria as
    linhas com ids novos ao retranscrever, então qualquer mudança altera isto.
    """
    count = len(rows)
    max_id = max((r["id"] for r in rows), default=0)
    return f"{count}:{max_id}"


def _project_segment_rows(project_id: int) -> list[Any]:
    conn = get_connection()
    return conn.execute(
        """
        SELECT s.id, s.audio_id, s.text, s.start, s."end", a.filename
        FROM segments s
        JOIN audios a ON a.id = s.audio_id
        WHERE a.project_id = ? AND s.text != ''
        ORDER BY a.created_at, a.id, s.seq
        """,
        (project_id,),
    ).fetchall()


def _compute(rows: list[Any]) -> dict[str, Any]:
    """Calcula o resumo de sentimento a partir das linhas de segmento (sem cache)."""
    predictions = _classify([r["text"] for r in rows])

    distribution = _empty_distribution()
    # Acumuladores por áudio: distribuição + média de polaridade (pos − neg).
    by_audio: dict[int, dict[str, Any]] = {}
    timeline: list[dict[str, Any]] = []

    for row, pred in zip(rows, predictions):
        label = pred["label"]
        distribution[label] += 1

        audio_id = row["audio_id"]
        agg = by_audio.get(audio_id)
        if agg is None:
            agg = {
                "audio_id": audio_id,
                "filename": row["filename"],
                "distribution": _empty_distribution(),
                "_polarity_sum": 0.0,
                "_count": 0,
            }
            by_audio[audio_id] = agg
        agg["distribution"][label] += 1
        # Polaridade contínua do trecho: P(pos) − P(neg), em [-1, 1].
        polarity = pred["scores"]["positive"] - pred["scores"]["negative"]
        agg["_polarity_sum"] += polarity
        agg["_count"] += 1

        timeline.append(
            {
                "segment_id": row["id"],
                "audio_id": audio_id,
                "start": row["start"],
                "label": label,
                "polarity": round(polarity, 4),
                "text": row["text"],
            }
        )

    audios = [
        {
            "audio_id": a["audio_id"],
            "filename": a["filename"],
            "distribution": a["distribution"],
            "avg_polarity": round(a["_polarity_sum"] / a["_count"], 4)
            if a["_count"]
            else 0.0,
        }
        for a in by_audio.values()
    ]

    total = sum(distribution.values())
    overall_polarity = (
        sum(t["polarity"] for t in timeline) / total if total else 0.0
    )
    return {
        "total_segments": total,
        "distribution": distribution,
        "avg_polarity": round(overall_polarity, 4),
        "audios": audios,
        "timeline": timeline,
        "signature": _signature(rows),
    }


def project_sentiment(project_id: int, *, refresh: bool = False) -> dict[str, Any]:
    """
    Resumo de sentimento do projeto, com cache na tabela `analyses`.

    Reaproveita o último resultado salvo se os segmentos não mudaram (mesma
    assinatura). `refresh=True` força o recálculo. A inferência é cara, então o
    cache evita reprocessar a transcrição inteira a cada visita à aba.
    """
    import repository as repo

    rows = _project_segment_rows(project_id)
    signature = _signature(rows)

    if not refresh:
        cached = repo.latest_analysis("sentiment", project_id=project_id)
        if cached is not None and cached["payload"].get("signature") == signature:
            return cached["payload"]

    summary = _compute(rows)
    repo.save_analysis("sentiment", summary, project_id=project_id)
    return summary
