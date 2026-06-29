"""
Caminhos de dados do Transcreve.

O áudio e o banco ficam no diretório de dados do usuário (por SO), nunca dentro
do repositório nem em nuvem. O Tauri pode sobrepor o diretório passando a env var
`TRANSCREVE_DATA_DIR` (o `app_data_dir` resolvido pelo Rust) no spawn do sidecar.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Transcreve"


def data_dir() -> Path:
    """
    Diretório base de dados do app, criado se necessário.

    Prioridade:
      1. `TRANSCREVE_DATA_DIR` (injetada pelo Tauri) — fonte de verdade no app.
      2. Convenção do SO (APPDATA / XDG / Application Support).
    """
    override = os.environ.get("TRANSCREVE_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        root = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        base = Path(root) / APP_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:  # Linux/BSD — XDG
        root = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
        base = Path(root) / APP_NAME

    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    """Caminho do arquivo SQLite (em <data_dir>/transcreve.sqlite)."""
    return data_dir() / "transcreve.sqlite"
