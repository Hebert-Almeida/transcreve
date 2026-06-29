"""
Configuração de runtime do sidecar quando empacotado (PyInstaller).

Em desenvolvimento nada muda: os modelos vêm do cache HF do usuário
(`~/.cache/huggingface/hub`) e a rede está disponível. No app empacotado
(`sys.frozen`), apontamos o Hugging Face para o cache embarcado no bundle e
forçamos modo offline — o app é 100% local, sem nenhuma chamada de rede em
runtime.

O cache embarcado é gravado pelo PyInstaller em `<bundle>/models` (ver o .spec),
com a estrutura padrão do HF (`models/hub/models--...`). `HF_HOME` aponta para
essa pasta `models`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True quando rodando dentro do bundle do PyInstaller."""
    return getattr(sys, "frozen", False)


def bundle_dir() -> Path:
    """Raiz dos recursos do bundle (`sys._MEIPASS` no onefile/onedir)."""
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) if base else Path(__file__).resolve().parent


def bundled_hf_home() -> Path | None:
    """Cache HF embarcado (`<bundle>/models`) quando frozen, senão None."""
    if not is_frozen():
        return None
    return bundle_dir() / "models"


def configure_offline() -> None:
    """
    Configura o HF para usar o cache embarcado e operar offline — só quando
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
