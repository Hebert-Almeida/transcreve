"""
Configuração de runtime do sidecar quando empacotado (PyInstaller).

Em desenvolvimento nada muda: os modelos vêm do cache HF do usuário
(`~/.cache/huggingface/hub`) e a rede está disponível. No app empacotado
(`sys.frozen`), apontamos o Hugging Face para um cache local e forçamos o modo
offline — o app é 100% local, sem nenhuma chamada de rede em runtime.

Os modelos NÃO ficam dentro do bundle do PyInstaller: 2,5 GB estouram o teto dos
instaladores do Windows (makensis mmap ~2 GB; WiX falha antes). Em vez disso, a
pasta `models/` (cache HF, ~2,5 GB) é entregue AO LADO do exe (empacotada como
resource do Tauri, em `<exe_dir>/models`). No primeiro boot copiamos esse cache
para o diretório de dados do app (`TRANSCREVE_DATA_DIR/models`) — persistente,
gravável e fora de "Program Files". Uma marca (`.seeded`) evita recópias.

`HF_HOME` aponta para o cache em app-data; a estrutura padrão do HF
(`models/hub/models--...`) é preservada.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True quando rodando dentro do bundle do PyInstaller."""
    return getattr(sys, "frozen", False)


def bundle_dir() -> Path:
    """Raiz dos recursos do bundle (`sys._MEIPASS` no onefile/onedir)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parent


def exe_dir() -> Path:
    """Pasta do executável congelado (onde fica o `models/` irmão)."""
    return Path(sys.executable).resolve().parent


def source_models_dir() -> Path | None:
    """Localiza o cache HF de origem (2,5 GB) entregue junto do app.

    Procura, em ordem: a env var TRANSCREVE_MODELS_DIR (injetada pelo Tauri, que
    sabe o resource_dir), depois `<exe_dir>/models` e `<exe_dir>/../models`.
    Retorna a primeira que existir com `hub/` dentro, ou None.
    """
    candidates = []
    env = os.environ.get("TRANSCREVE_MODELS_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(exe_dir() / "models")
    candidates.append(exe_dir().parent / "models")
    for c in candidates:
        if (c / "hub").is_dir():
            return c
    return None


def data_dir() -> Path:
    """Diretório de dados do app, injetado pelo Tauri (fallback p/ ao lado do exe)."""
    env = os.environ.get("TRANSCREVE_DATA_DIR")
    return Path(env) if env else exe_dir()


def target_models_dir() -> Path:
    """Cache HF persistente em app-data (`<data_dir>/models`)."""
    return data_dir() / "models"


def _seed_models(src: Path | None, dst: Path) -> bool:
    """Copia o cache de modelos `src` -> `dst` no primeiro boot (idempotente).

    Retorna True se `dst` está pronto (semeado agora ou já semeado antes).
    Guardado por uma marca `.seeded` para não recopiar 2,5 GB a cada boot.
    Se `src` for None (ex.: rodando o exe fora do instalador), não falha:
    apenas retorna se `dst` já tem o cache.
    """
    marker = dst / ".seeded"
    if marker.exists():
        return True
    if src is None:
        # Sem fonte para semear; só serve se já houver hub/ no destino.
        return (dst / "hub").is_dir()

    dst.mkdir(parents=True, exist_ok=True)
    # robocopy (não shutil): os caminhos do cache HF (snapshots/<hash>/arquivo)
    # passam de 260 chars e estouram o shutil.copytree (WinError 206). O robocopy
    # lida com caminhos longos nativamente. /E copia subpastas (inclui vazias).
    result = subprocess.run(
        ["robocopy", str(src), str(dst), "/E",
         "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP"],
        capture_output=True,
    )
    # robocopy: códigos 0-7 são sucesso; >= 8 é erro real.
    if result.returncode >= 8:
        raise RuntimeError(
            f"robocopy falhou ao semear modelos (código {result.returncode})"
        )
    marker.write_text("ok", encoding="utf-8")
    return True


def bundled_hf_home() -> Path | None:
    """HF_HOME a usar quando frozen (app-data), semeando os modelos se preciso.

    Retorna None em dev (usa o cache do usuário e a rede).
    """
    if not is_frozen():
        return None
    target = target_models_dir()
    _seed_models(source_models_dir(), target)
    return target


def configure_offline() -> None:
    """
    Configura o HF para usar o cache local e operar offline — só quando
    empacotado. Idempotente (usa setdefault) e seguro em dev (no-op).

    Deve ser chamado o mais cedo possível, antes de importar
    faster_whisper/transformers/pysentimiento, pois essas libs leem as env vars
    de cache/offline no import.
    """
    # Silencia o aviso de symlinks do HF no Windows em qualquer cenário.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    hf_home = bundled_hf_home()
    if hf_home is None:
        return  # dev: usa o cache do usuário e a rede normalmente.

    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
