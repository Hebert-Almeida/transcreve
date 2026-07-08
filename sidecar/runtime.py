"""
Configuração de runtime do sidecar quando empacotado (PyInstaller).

Em desenvolvimento nada muda: os modelos vêm do cache HF do usuário
(`~/.cache/huggingface/hub`) e a rede está disponível. No app empacotado
(`sys.frozen`), apontamos o Hugging Face para o cache local de modelos e
forçamos o modo offline — o app é 100% local, sem nenhuma chamada de rede
em runtime.

Os modelos (~2,5 GB) NÃO viajam dentro do instalador: o NSIS usa mmap e falha
perto de ~2 GB. Eles chegam por dois caminhos, e o Tauri informa qual via
`TRANSCREVE_MODELS_DIR`:

  - Versão instalada: o instalador NSIS baixa os modelos durante a instalação
    para `C:\\ProgramData\\Transcreve\\models` (compartilhado, fora de Program
    Files — sobrevive a atualizações e desinstalações, sem recópia).
  - Versão portátil: o zip já traz `models/` ao lado do exe do app.

Nos dois casos a pasta contém o layout padrão do cache HF (`hub/models--...`),
então basta apontar `HF_HOME` para ela — sem cópia nenhuma no primeiro boot.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True quando rodando dentro do bundle do PyInstaller."""
    return getattr(sys, "frozen", False)


def exe_dir() -> Path:
    """Pasta do executável congelado."""
    return Path(sys.executable).resolve().parent


def models_dir() -> Path:
    """Raiz do cache de modelos (contém `hub/`), definida pelo Tauri.

    O sidecar.rs é a fonte da verdade: ele resolve o local (ProgramData na
    versão instalada, `<pasta do app>\\models` na portátil) e o injeta em
    `TRANSCREVE_MODELS_DIR` — no app real a variável está SEMPRE presente. O
    fallback exe-relativo só é alcançado ao rodar o exe congelado à mão, fora do
    app, e assume o layout portátil (modelos ao lado do exe).
    """
    env = os.environ.get("TRANSCREVE_MODELS_DIR")
    if env:
        return Path(env)
    return exe_dir() / "models"


def data_dir() -> Path:
    """Diretório de dados do app (banco, áudios), injetado pelo Tauri."""
    env = os.environ.get("TRANSCREVE_DATA_DIR")
    return Path(env) if env else exe_dir() / "data"


def model_available(pattern: str) -> bool:
    """Confere se um modelo existe no cache local (`hub/models--<pattern>`).

    `pattern` é um glob aplicado ao nome da pasta do cache HF, ex.:
    `*faster-whisper-small` ou `pysentimiento--*`. Só é significativo quando
    frozen; em dev retorna True (o HF baixa sob demanda, com rede).
    """
    if not is_frozen():
        return True
    hub = models_dir() / "hub"
    for entry in hub.glob(f"models--{pattern}"):
        if any(entry.glob("snapshots/*/*")):
            return True
    return False


def missing_models_error(what: str) -> RuntimeError:
    """Erro amigável (PT-BR) quando o cache de modelos não está no lugar.

    A mensagem chega intacta à interface (evento `error` do stream), então ela
    precisa dizer ao usuário final o que fazer — não a um desenvolvedor.
    """
    return RuntimeError(
        f"O modelo de IA ({what}) não foi encontrado neste computador "
        f"(esperado em: {models_dir()}). "
        "Se você usou o instalador, execute-o novamente — ele baixa os modelos "
        "que faltam e retoma downloads incompletos. Se você usa a versão "
        "portátil, confira se a pasta 'models' foi extraída junto com o "
        "programa. Nenhum dado seu sai do computador."
    )


def require_model(pattern: str, what: str) -> None:
    """Garante que o modelo `pattern` está no cache; senão, erro amigável (PT-BR).

    Empacotado e offline, um cache ausente faria o HF soltar um erro técnico
    ilegível ("Cannot find an appropriate cached snapshot..."). Antecipamos com
    uma mensagem que orienta o usuário final. Em dev é no-op (o HF baixa sob
    demanda, com rede) — ver [`model_available`].
    """
    if not model_available(pattern):
        raise missing_models_error(what)


def configure_offline() -> None:
    """
    Aponta o Hugging Face para o cache local e liga o modo offline — só quando
    empacotado. Idempotente (usa setdefault) e seguro em dev (no-op).

    Deve ser chamado o mais cedo possível, antes de importar
    faster_whisper/transformers/pysentimiento, pois essas libs leem as env vars
    de cache/offline no import.
    """
    # Silencia o aviso de symlinks do HF no Windows em qualquer cenário.
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    if not is_frozen():
        return  # dev: usa o cache do usuário e a rede normalmente.

    os.environ.setdefault("HF_HOME", str(models_dir()))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
