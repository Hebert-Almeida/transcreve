"""
Build do sidecar congelado e instalação no diretório de binários do Tauri.

Roda o PyInstaller com `transcreve-sidecar.spec` (onedir) e espelha o resultado
(exe + `_internal/`) para `src-tauri/binaries/`. Essa pasta é embarcada como
`resource` do Tauri; o sidecar.rs resolve `binaries/transcreve-sidecar.exe` via
resource_dir() e o executa diretamente (NÃO usamos `externalBin`, que empacota
um único arquivo e não carregaria o `_internal/` irmão que o PyInstaller onedir
exige).

Os modelos de IA (~2,5 GB) NÃO entram no bundle — estouram o teto do instalador.
Quem os entrega é: o instalador NSIS (baixa durante a instalação) e o ZIP
portátil (scripts/release.py monta models/hub a partir do cache HF). O runtime
os localiza por TRANSCREVE_MODELS_DIR, injetado pelo sidecar.rs.

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

    # Espelha via robocopy — mais robusto que shutil para árvores grandes.
    # /MIR mantém binaries/ idêntico ao dist/ (limpa sobras de builds antigas,
    # inclusive a pasta models/ que builds anteriores chegaram a copiar aqui).
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
    install_to_tauri()
