"""
Sidecar do Transcreve — servidor local FastAPI.

Roda em localhost e é gerenciado pelo processo Tauri (spawn/teardown). Expõe a
transcrição, a persistência (projetos/áudios/segmentos/códigos), as análises e a
exportação. Nada sai da máquina do usuário.

Execução em desenvolvimento:
    uvicorn app:app --host 127.0.0.1 --port 8756
"""
from __future__ import annotations

import sqlite3
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from urllib.parse import quote
from pydantic import BaseModel

import repository as repo
from config import detect_hardware
from db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria/migra o banco antes de atender requisições.
    init_db()
    yield


app = FastAPI(
    title="Transcreve Sidecar",
    description="Serviço local de transcrição e análise de áudios de pesquisa.",
    version="0.1.0",
    lifespan=lifespan,
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


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error_handler(request: Request, exc: sqlite3.IntegrityError):
    """
    Violação de restrição do banco (UNIQUE, FK) é entrada inválida do cliente,
    não falha do servidor — responde 409 com JSON em vez de vazar um 500.
    """
    return JSONResponse(
        status_code=409,
        content={"detail": "Conflito de dados", "error": str(exc)},
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


# --- Projetos ------------------------------------------------------------


class ProjectIn(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@app.get("/projects")
def list_projects():
    return repo.list_projects()


@app.post("/projects", status_code=201)
def create_project(body: ProjectIn):
    return repo.create_project(body.name, body.description)


@app.get("/projects/{project_id}")
def get_project(project_id: int):
    project = repo.get_project(project_id)
    if project is None:
        raise HTTPException(404, "Projeto não encontrado")
    return project


@app.patch("/projects/{project_id}")
def update_project(project_id: int, body: ProjectUpdate):
    project = repo.update_project(project_id, body.name, body.description)
    if project is None:
        raise HTTPException(404, "Projeto não encontrado")
    return project


@app.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: int):
    if not repo.delete_project(project_id):
        raise HTTPException(404, "Projeto não encontrado")


# --- Áudios --------------------------------------------------------------


class AudioIn(BaseModel):
    path: str
    filename: str
    duration: float | None = None
    language: str | None = None
    model: str | None = None
    device: str | None = None


@app.get("/projects/{project_id}/audios")
def list_audios(project_id: int):
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    return repo.list_audios(project_id)


@app.post("/projects/{project_id}/audios", status_code=201)
def create_audio(project_id: int, body: AudioIn):
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    return repo.create_audio(
        project_id,
        body.path,
        body.filename,
        duration=body.duration,
        language=body.language,
        model=body.model,
        device=body.device,
    )


@app.get("/audios/{audio_id}")
def get_audio(audio_id: int):
    audio = repo.get_audio(audio_id)
    if audio is None:
        raise HTTPException(404, "Áudio não encontrado")
    return audio


@app.delete("/audios/{audio_id}", status_code=204)
def delete_audio(audio_id: int):
    if not repo.delete_audio(audio_id):
        raise HTTPException(404, "Áudio não encontrado")


@app.get("/audios/{audio_id}/segments")
def list_segments(audio_id: int):
    if repo.get_audio(audio_id) is None:
        raise HTTPException(404, "Áudio não encontrado")
    return repo.list_segments(audio_id)


# --- Códigos / codificação qualitativa ----------------------------------


class CodeIn(BaseModel):
    name: str
    color: str | None = None


class AssignIn(BaseModel):
    segment_id: int
    code_id: int
    memo: str | None = None


@app.get("/projects/{project_id}/codes")
def list_codes(project_id: int):
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    return repo.list_codes(project_id)


@app.post("/projects/{project_id}/codes", status_code=201)
def create_code(project_id: int, body: CodeIn):
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    return repo.create_code(project_id, body.name, body.color)


@app.delete("/codes/{code_id}", status_code=204)
def delete_code(code_id: int):
    if not repo.delete_code(code_id):
        raise HTTPException(404, "Código não encontrado")


@app.post("/codes/assign", status_code=204)
def assign_code(body: AssignIn):
    repo.assign_code(body.segment_id, body.code_id, body.memo)


@app.post("/codes/unassign", status_code=204)
def unassign_code(body: AssignIn):
    if not repo.unassign_code(body.segment_id, body.code_id):
        raise HTTPException(404, "Vínculo não encontrado")


@app.get("/codes/{code_id}/segments")
def segments_for_code(code_id: int):
    return repo.segments_for_code(code_id)


@app.get("/segments/{segment_id}/codes")
def codes_for_segment(segment_id: int):
    return repo.codes_for_segment(segment_id)


@app.get("/audios/{audio_id}/coding")
def coding_for_audio(audio_id: int):
    """Mapa segment_id -> códigos, para a UI destacar trechos codificados."""
    if repo.get_audio(audio_id) is None:
        raise HTTPException(404, "Áudio não encontrado")
    # Chaves JSON são strings — a UI lê por String(segment_id).
    return {str(k): v for k, v in repo.coding_for_audio(audio_id).items()}


# --- Análise qualitativa -------------------------------------------------


@app.get("/projects/{project_id}/analysis/qualitative")
def qualitative_analysis(project_id: int):
    """Frequência de códigos, co-ocorrência e cobertura da codificação."""
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    from analysis.qualitative import qualitative_summary

    return qualitative_summary(project_id)


# --- Análise quantitativa ------------------------------------------------


@app.get("/audios/{audio_id}/analysis/quantitative")
def quantitative_audio_analysis(audio_id: int):
    """Métricas descritivas de um áudio: palavras, velocidade, riqueza, termos."""
    if repo.get_audio(audio_id) is None:
        raise HTTPException(404, "Áudio não encontrado")
    from analysis.quantitative import audio_metrics

    return audio_metrics(audio_id)


@app.get("/projects/{project_id}/analysis/quantitative")
def quantitative_project_analysis(project_id: int):
    """Métricas quantitativas agregadas do projeto, com recorte por áudio."""
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    from analysis.quantitative import project_metrics

    return project_metrics(project_id)


# --- Análise de sentimento -----------------------------------------------


@app.get("/projects/{project_id}/analysis/sentiment")
def sentiment_analysis(project_id: int, refresh: bool = False):
    """
    Distribuição de sentimento (positivo/negativo/neutro) do projeto, com
    recorte por áudio e linha do tempo. Resultado é cacheado (inferência cara);
    `refresh=true` força o recálculo.
    """
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    from analysis.sentiment import project_sentiment

    return project_sentiment(project_id, refresh=refresh)


# --- Exportação ----------------------------------------------------------


def _download(make_export) -> Response:
    """Roda o exportador e embrulha o `Export` numa resposta de download.

    `make_export` é a chamada (sem argumentos) que produz o `Export`. Formato/tipo
    de análise inválidos viram `ValueError` → 400; o resto vira anexo com
    Content-Disposition (RFC 5987 para nomes com acento).
    """
    try:
        export = make_export()
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    disposition = f"attachment; filename*=UTF-8''{quote(export.filename)}"
    return Response(
        content=export.content,
        media_type=export.media_type,
        headers={"Content-Disposition": disposition},
    )


@app.get("/audios/{audio_id}/export/{fmt}")
def export_audio_transcript(audio_id: int, fmt: str, coding: bool = False):
    """Transcrição de um áudio (csv|tsv|json|srt|vtt|docx|pdf)."""
    if repo.get_audio(audio_id) is None:
        raise HTTPException(404, "Áudio não encontrado")
    from export.transcript import export_transcript

    return _download(
        lambda: export_transcript(fmt, audio_id=audio_id, include_coding=coding)
    )


@app.get("/projects/{project_id}/export/{fmt}")
def export_project_transcript(project_id: int, fmt: str, coding: bool = False):
    """Transcrição de todos os áudios do projeto (mesmos formatos)."""
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    from export.transcript import export_transcript

    return _download(
        lambda: export_transcript(fmt, project_id=project_id, include_coding=coding)
    )


@app.get("/projects/{project_id}/analysis/{kind}/export/{fmt}")
def export_project_analysis(project_id: int, kind: str, fmt: str):
    """Resultado de uma análise do projeto (quantitative|sentiment em csv|tsv|json)."""
    if repo.get_project(project_id) is None:
        raise HTTPException(404, "Projeto não encontrado")
    from export.analysis import export_analysis

    return _download(lambda: export_analysis(kind, fmt, project_id=project_id))


# --- Transcrição ---------------------------------------------------------


class TranscribeRequest(BaseModel):
    audio_path: str
    language: str | None = None
    model: str | None = None
    device: str = "auto"
    # Se informado, o resultado é persistido nesse áudio (segmentos + metadados).
    audio_id: int | None = None


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

    Se `audio_id` for informado, persiste os segmentos e atualiza o status/metadados
    do áudio no banco — fonte única de verdade para a UI e as análises.
    """
    from transcribe import transcribe as run_transcribe

    if req.audio_id is not None:
        repo.update_audio_status(req.audio_id, "processing")

    try:
        result = run_transcribe(
            req.audio_path,
            language=req.language,
            model=req.model,
            device=req.device,  # type: ignore[arg-type]
        )
    except Exception:
        if req.audio_id is not None:
            repo.update_audio_status(req.audio_id, "error")
        raise

    if req.audio_id is not None:
        repo.replace_segments(
            req.audio_id,
            [
                {
                    "seq": s.id,
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "speaker": s.speaker,
                    "words": [
                        {
                            "start": w.start,
                            "end": w.end,
                            "word": w.word,
                            "probability": w.probability,
                        }
                        for w in s.words
                    ],
                }
                for s in result.segments
            ],
        )
        repo.update_audio_status(
            req.audio_id,
            "done",
            duration=result.duration,
            language=result.language,
            model=result.model,
            device=result.device,
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
