"""
Wrapper de transcrição sobre faster-whisper.

Carrega o modelo Whisper (large-v3-turbo por padrão, com fallback para máquinas
modestas), transcreve áudios longos com timestamps por palavra e reporta
progresso por segmento. A diarização (pyannote) será adicionada numa fase futura.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Iterable

# Silencia aviso de symlinks do huggingface_hub no Windows (cache funciona igual).
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from config import Device, default_compute_type, resolve_device, suggest_model


@dataclass
class Word:
    start: float
    end: float
    word: str
    probability: float | None = None


@dataclass
class Segment:
    id: int
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)
    # Reservado para a diarização futura (rótulo do falante).
    speaker: str | None = None


@dataclass
class TranscriptionResult:
    language: str
    language_probability: float
    duration: float
    segments: list[Segment]
    model: str
    device: str


# O modelo é caro de carregar; mantemos um cache por (modelo, device, compute).
@lru_cache(maxsize=2)
def _load_model(model: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel  # import tardio: só quando há transcrição

    return WhisperModel(model, device=device, compute_type=compute_type)


def transcribe(
    audio_path: str,
    *,
    language: str | None = None,
    model: str | None = None,
    device: Device = "auto",
    word_timestamps: bool = True,
    on_progress: Callable[[Segment, float], None] | None = None,
) -> TranscriptionResult:
    """
    Transcreve `audio_path`.

    - `language=None` deixa o Whisper detectar (PT/EN/ES etc.).
    - `on_progress(segment, fraction)` é chamado a cada segmento, com a fração
      estimada (0..1) pela razão entre o tempo do segmento e a duração total.
    """
    resolved_model = suggest_model(model)
    resolved_device = resolve_device(device)
    compute_type = default_compute_type(resolved_device)

    whisper = _load_model(resolved_model, resolved_device, compute_type)

    segments_iter, info = whisper.transcribe(
        audio_path,
        language=language,
        word_timestamps=word_timestamps,
        vad_filter=True,  # remove silêncios longos — ajuda em áudios de pesquisa
    )

    total = float(getattr(info, "duration", 0.0)) or 0.0
    segments = list(_collect(segments_iter, total, on_progress))

    return TranscriptionResult(
        language=info.language,
        language_probability=float(getattr(info, "language_probability", 0.0)),
        duration=total,
        segments=segments,
        model=resolved_model,
        device=resolved_device,
    )


def _collect(
    raw_segments: Iterable,
    total: float,
    on_progress: Callable[[Segment, float], None] | None,
) -> Iterable[Segment]:
    for raw in raw_segments:
        words = [
            Word(
                start=float(w.start),
                end=float(w.end),
                word=w.word,
                probability=getattr(w, "probability", None),
            )
            for w in (raw.words or [])
        ]
        seg = Segment(
            id=raw.id,
            start=float(raw.start),
            end=float(raw.end),
            text=raw.text.strip(),
            words=words,
        )
        if on_progress and total > 0:
            on_progress(seg, min(seg.end / total, 1.0))
        yield seg
