"""
Build do sidecar congelado e instalação no diretório de binários do Tauri.

Roda o PyInstaller com `transcreve-sidecar.spec` (onedir), copia o cache HF dos
modelos para dentro do bundle e espelha o resultado (exe + `_internal/`) para
`src-tauri/binaries/`. Essa pasta é embarcada como `resource` do Tauri; o
sidecar.rs resolve `binaries/transcreve-sidecar.exe` via resource_dir() e o
executa diretamente (NÃO usamos `externalBin`, que empacota um único arquivo e
não carregaria o `_internal/` irmão que o PyInstaller onedir exige).

Uso (na .venv312):
    cd sidecar
    .venv312/Scripts/python build.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SIDECAR_DIR = Path(__file__).resolve().parent
REPO_ROOT = SIDECAR_DIR.parent
DIST_DIR = SIDECAR_DIR / "dist" / "transcreve-sidecar"
# Em onedir, sys._MEIPASS aponta para _internal/; runtime.bundled_hf_home() =
# <_MEIPASS>/models, e o HF espera models/hub/ dentro dele.
MODELS_DEST = DIST_DIR / "_internal" / "models" / "hub"
HF_HUB = Path.home() / ".cache" / "huggingface" / "hub"
BIN_DIR = REPO_ROOT / "src-tauri" / "binaries"


def _purge_dir(target: Path) -> None:
    """Apaga `target` mesmo com caminhos > 260 chars (espelha um dir vazio).

    O shutil/os do PyInstaller falha ao limpar `dist/` quando ele contém o cache
    HF dos modelos (snapshots/<hash>/preprocessor_config.json estoura o MAX_PATH).
    O robocopy /MIR a partir de um diretório vazio remove a árvore inteira.
    """
    if not target.exists():
        return
    empty = SIDECAR_DIR / "_empty_purge"
    empty.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["robocopy", str(empty), str(target), "/MIR",
         "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP"],
    )
    shutil.rmtree(target, ignore_errors=True)
    shutil.rmtree(empty, ignore_errors=True)


def run_pyinstaller() -> None:
    spec = SIDECAR_DIR / "transcreve-sidecar.spec"
    # PyInstaller limpa dist/ com shutil (sem suporte a caminho longo) e morre se
    # os modelos de uma build anterior estiverem lá. Purgamos antes via robocopy.
    print(f"[build] limpando build anterior em {DIST_DIR}…")
    _purge_dir(DIST_DIR)
    print(f"[build] PyInstaller {spec.name} (onedir)…")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"],
        cwd=SIDECAR_DIR,
        check=True,
    )


def copy_models() -> None:
    """Copia o cache HF dos modelos para _internal/models/hub/ via robocopy.

    Feito FORA do PyInstaller porque a estrutura hub/snapshots/<hash>/arquivo
    estoura o limite de 260 caracteres do COLLECT. O robocopy lida com caminhos
    longos nativamente (e /MIR mantém o destino idêntico à origem).
    """
    if not HF_HUB.exists():
        raise SystemExit(
            f"[build] cache HF não encontrado em {HF_HUB}. Rode a Etapa 0 (download)."
        )
    MODELS_DEST.mkdir(parents=True, exist_ok=True)
    print(f"[build] copiando modelos {HF_HUB} -> {MODELS_DEST} (robocopy)…")
    # robocopy: códigos de saída 0-7 são sucesso; >=8 é erro real.
    result = subprocess.run(
        [
            "robocopy",
            str(HF_HUB),
            str(MODELS_DEST),
            "/MIR",  # espelha a árvore
            "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP",  # saída enxuta
        ],
    )
    if result.returncode >= 8:
        raise SystemExit(f"[build] robocopy falhou (código {result.returncode})")
    print("[build] modelos copiados.")


def install_to_tauri() -> None:
    """Espelha o onedir (exe + _internal/) para `src-tauri/binaries/`.

    Esse diretório é embarcado como `resource` no tauri.conf.json; o sidecar.rs
    resolve `binaries/transcreve-sidecar.exe` via resource_dir() e o executa
    diretamente. Mantemos o nome simples do exe (sem sufixo de target-triple) —
    o sufixo só faria sentido no `externalBin`, que NÃO usamos por ser one-file.
    """
    if not DIST_DIR.exists():
        raise SystemExit(f"[build] saída não encontrada: {DIST_DIR}")

    exe_in = DIST_DIR / "transcreve-sidecar.exe"
    if not exe_in.exists():
        raise SystemExit(f"[build] exe não encontrado em {exe_in}")

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    # Espelha via robocopy — os caminhos dos modelos passam de 260 chars, fora do
    # alcance do shutil. /MIR mantém binaries/ idêntico ao dist/ (limpa sobras).
    print(f"[build] espelhando bundle -> {BIN_DIR} (robocopy)…")
    result = subprocess.run(
        [
            "robocopy",
            str(DIST_DIR),
            str(BIN_DIR),
            "/MIR",
            "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP",
        ],
    )
    if result.returncode >= 8:
        raise SystemExit(f"[build] robocopy falhou (código {result.returncode})")

    print(f"[build] OK: {BIN_DIR / 'transcreve-sidecar.exe'}")


if __name__ == "__main__":
    run_pyinstaller()
    copy_models()  # popula dist/.../_internal/models antes de espelhar p/ binaries
    install_to_tauri()
