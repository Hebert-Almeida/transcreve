"""
Build do sidecar congelado e instalação no diretório de binários do Tauri.

Roda o PyInstaller com `transcreve-sidecar.spec` (onedir) e copia o resultado
para `src-tauri/binaries/`, renomeando o `.exe` com o sufixo do target-triple
que o Tauri exige no `externalBin` (ex.: `-x86_64-pc-windows-msvc`).

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


def target_triple() -> str:
    """Target-triple do Rust (via `rustc -vV`); fallback p/ Windows x64 MSVC."""
    try:
        out = subprocess.run(
            ["rustc", "-vV"], capture_output=True, text=True, check=True
        ).stdout
        for line in out.splitlines():
            if line.startswith("host:"):
                return line.split("host:", 1)[1].strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    # Fallback: o Tauri no Windows usa o toolchain MSVC.
    return "x86_64-pc-windows-msvc"


def run_pyinstaller() -> None:
    spec = SIDECAR_DIR / "transcreve-sidecar.spec"
    print(f"[build] PyInstaller {spec.name} (onedir)…")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec), "--noconfirm"],
        cwd=SIDECAR_DIR,
        check=True,
    )


def install_to_tauri() -> None:
    if not DIST_DIR.exists():
        raise SystemExit(f"[build] saída não encontrada: {DIST_DIR}")

    triple = target_triple()
    exe_in = DIST_DIR / "transcreve-sidecar.exe"
    if not exe_in.exists():
        raise SystemExit(f"[build] exe não encontrado em {exe_in}")

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    # Copia o conteúdo do onedir (exe + _internal/) para binaries/, renomeando o
    # exe com o sufixo do triple. O Tauri resolve o sidecar por esse nome.
    dest_exe = BIN_DIR / f"transcreve-sidecar-{triple}.exe"
    print(f"[build] copiando bundle -> {BIN_DIR} (exe: {dest_exe.name})")

    for item in DIST_DIR.iterdir():
        if item.name == "transcreve-sidecar.exe":
            shutil.copy2(item, dest_exe)
        elif item.is_dir():
            dst = BIN_DIR / item.name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(item, dst)
        else:
            shutil.copy2(item, BIN_DIR / item.name)

    print(f"[build] OK: {dest_exe}")


if __name__ == "__main__":
    run_pyinstaller()
    install_to_tauri()
