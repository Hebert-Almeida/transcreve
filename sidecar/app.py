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
from pydantic import BaseModel

app = FastAPI(
    title="Transcreve Sidecar",
    description="Serviço local de transcrição e análise de áudios de pesquisa.",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    status: str
    version: str
    python: str


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Usado pelo Tauri para confirmar que o sidecar subiu."""
    return HealthResponse(
        status="ok",
        version=app.version,
        python=sys.version.split()[0],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8756)
