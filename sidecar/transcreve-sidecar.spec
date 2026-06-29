# -*- mode: python ; coding: utf-8 -*-
"""
Spec do PyInstaller para o sidecar do Transcreve (binário congelado offline).

Gera um bundle **one-folder** (onedir) — onefile extrairia ~1.3GB a cada boot.
Embarca o cache HF dos 3 modelos em `models/hub/` para que
`runtime.bundled_hf_home()` (HF_HOME=<bundle>/models) os encontre offline.

Uso:
    cd sidecar
    .venv312/Scripts/pyinstaller transcreve-sidecar.spec --noconfirm

Saída: dist/transcreve-sidecar/ (pasta) com transcreve-sidecar.exe dentro.
O build.py copia/renomeia para src-tauri/binaries/ com o sufixo do target-triple
que o Tauri exige.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

SIDECAR_DIR = Path(SPECPATH)  # noqa: F821 (SPECPATH é injetado pelo PyInstaller)
HF_HUB = Path.home() / ".cache" / "huggingface" / "hub"

# --- Modelos: embarca o cache HF em models/hub/ -------------------------------
# Cada arquivo do cache vira (origem_absoluta, destino_relativo_no_bundle).
model_datas = []
if HF_HUB.exists():
    for f in HF_HUB.rglob("*"):
        if f.is_file():
            rel = f.relative_to(HF_HUB)
            dest = str(Path("models") / "hub" / rel.parent)
            model_datas.append((str(f), dest))
else:
    raise SystemExit(
        f"Cache HF não encontrado em {HF_HUB}. Rode a Etapa 0 (download dos modelos) antes."
    )

# --- Data files e submódulos das libs de IA -----------------------------------
# transformers/tokenizers/pysentimiento carregam recursos por nome em runtime;
# collect_data_files garante que .json/.txt/etc. acompanhem o bundle.
datas = list(model_datas)
for pkg in ("pysentimiento", "transformers", "tokenizers", "huggingface_hub"):
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
    runtime_hooks=[],
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
