# -*- mode: python ; coding: utf-8 -*-
"""
Spec do PyInstaller para o sidecar do Transcreve (binário congelado offline).

Gera um bundle **one-folder** (onedir) — onefile extrairia ~1.3GB a cada boot.
Os modelos de IA (~2,5 GB) NÃO entram no bundle: são entregues à parte (o
instalador NSIS os baixa; o ZIP portátil os traz montados por
scripts/release.py) e localizados em runtime via TRANSCREVE_MODELS_DIR.

Uso:
    cd sidecar
    .venv312/Scripts/pyinstaller transcreve-sidecar.spec --noconfirm

Saída: dist/transcreve-sidecar/ (pasta) com transcreve-sidecar.exe dentro.
O build.py espelha essa pasta para src-tauri/binaries/ (embarcada como resource
do Tauri; sem sufixo de target-triple, pois não usamos externalBin).
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

SIDECAR_DIR = Path(SPECPATH)  # noqa: F821 (SPECPATH é injetado pelo PyInstaller)

# --- Data files e submódulos das libs de IA -----------------------------------
# OBS: o cache HF dos modelos NÃO é embarcado aqui (nem em lugar nenhum do
# bundle) — 2,5 GB estouram o teto do instalador e a estrutura
# hub/snapshots/<hash>/arquivo estoura o MAX_PATH do COLLECT. A entrega dos
# modelos é externa (instalador baixa / ZIP portátil traz), descrita no topo.
#
# transformers/tokenizers/pysentimiento carregam recursos por nome em runtime;
# collect_data_files garante que .json/.txt/etc. acompanhem o bundle.
datas = []
for pkg in (
    "faster_whisper",  # traz assets/silero_vad_v6.onnx (modelo VAD usado em runtime)
    "pysentimiento",
    "transformers",
    "tokenizers",
    "huggingface_hub",
):
    datas += collect_data_files(pkg)

hiddenimports = []
for pkg in (
    "faster_whisper",
    "ctranslate2",
    "pysentimiento",
    "transformers",
    "tokenizers",
    "sentencepiece",
    "torch",
    "onnxruntime",
    "av",
):
    hiddenimports += collect_submodules(pkg)

a = Analysis(
    ["app.py"],
    pathex=[str(SIDECAR_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    # Registra _MEIPASS (+ torch/lib) como dirs de DLL antes dos imports — corrige
    # WinError 1114 ao carregar c10.dll/fbgemm.dll no torch. Ver rthook_dll_dirs.py.
    runtime_hooks=["rthook_dll_dirs.py"],
    excludes=[
        "tkinter",
        "matplotlib",
        "PyQt5",
        "PySide2",
        "pytest",
        "IPython",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- Runtime VC++ / UCRT consistente -----------------------------------------
# O PyInstaller às vezes coleta um conjunto MISTURADO do runtime do Visual C++
# (ex.: msvcp140.dll 14.29 ao lado de vcruntime140.dll 14.42). c10.dll do torch,
# compilado com um toolset novo, falha na inicialização (WinError 1114) quando o
# msvcp140 é antigo demais para os símbolos que ele importa.
#
# Correção: removemos as cópias coletadas desses DLLs e as substituímos pelas do
# System32 (um único conjunto coerente, instalado pelo VC++ Redistributable),
# garantindo um app 100% offline sem depender do runtime da máquina-alvo.
_VC_RUNTIME = {
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll",
    "msvcp140_codecvt_ids.dll",
    "concrt140.dll",
}
a.binaries = [b for b in a.binaries if Path(b[0]).name.lower() not in _VC_RUNTIME]

_system32 = Path("C:/Windows/System32")
for name in sorted(_VC_RUNTIME):
    src = _system32 / name
    if src.exists():
        a.binaries.append((name, str(src), "BINARY"))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: binários ficam no COLLECT, não no exe
    name="transcreve-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # sidecar headless; logs vão ao stdout/stderr (capturados pelo Tauri)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="transcreve-sidecar",
)
