"""
Sidecar do Transcreve — servidor local FastAPI.

Roda em localhost e é gerenciado pelo processo Tauri (spawn/teardown). Expõe a
transcrição, as análises e a exportação. Nada sai da máquina do usuário.

Execução em desenvolvimento:
    uvicorn app:app --host 127.0.0.1 --port 8756
"""
from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import detect_hardware

app = FastAPI(
    title="Transcreve Sidecar",
    description="Serviço local de transcrição e análise de áudios de pesquisa.",
    version="0.1.0",
)

# O WebView do Tauri faz preflight CORS. O sidecar só escuta em 127.0.0.1,
# então liberamos as origens do app (dev e produção) com segurança.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",  # Vite dev
        "http://127.0.0.1:1420",
        "tauri://localhost",  # produção (macOS/Linux)
        "http://tauri.localhost",  # produção (Windows)
        "https://tauri.localhost",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    version: str
    python: str


class HardwareResponse(BaseModel):
    has_cuda: bool
    cuda_device_name: str | None
    total_ram_gb: float | None


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Usado pelo Tauri para confirmar que o sidecar subiu."""
    return HealthResponse(
        status="ok",
        version=app.version,
        python=sys.version.split()[0],
    )


@app.get("/hardware", response_model=HardwareResponse)
def hardware() -> HardwareResponse:
    """Hardware detectado — a UI usa para pré-selecionar CPU/GPU."""
    hw = detect_hardware()
    return HardwareResponse(
        has_cuda=hw.has_cuda,
        cuda_device_name=hw.cuda_device_name,
        total_ram_gb=hw.total_ram_gb,
    )


# --- Transcrição ---------------------------------------------------------


class TranscribeRequest(BaseModel):
    audio_path: str
    language: str | None = None
    model: str | None = None
    device: str = "auto"


class WordOut(BaseModel):
    start: float
    end: float
    word: str
    probability: float | None = None


class SegmentOut(BaseModel):
    id: int
    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[WordOut] = []


class TranscribeResponse(BaseModel):
    language: str
    language_probability: float
    duration: float
    model: str
    device: str
    segments: list[SegmentOut]


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe_endpoint(req: TranscribeRequest) -> TranscribeResponse:
    """
    Transcreve um áudio (caminho local). Síncrono por ora; uma versão com
    progresso em tempo real (WebSocket) virá em seguida.
    """
    from transcribe import transcribe as run_transcribe

    result = run_transcribe(
        req.audio_path,
        language=req.language,
        model=req.model,
        device=req.device,  # type: ignore[arg-type]
    )
    return TranscribeResponse(
        language=result.language,
        language_probability=result.language_probability,
        duration=result.duration,
        model=result.model,
        device=result.device,
        segments=[
            SegmentOut(
                id=s.id,
                start=s.start,
                end=s.end,
                text=s.text,
                speaker=s.speaker,
                words=[
                    WordOut(start=w.start, end=w.end, word=w.word, probability=w.probability)
                    for w in s.words
                ],
            )
            for s in result.segments
        ],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8756)
