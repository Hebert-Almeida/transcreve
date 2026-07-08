"""
Ferramentas de release do Transcreve — gera o manifesto NSIS dos modelos,
prepara os arquivos (assets) da release `modelos-v1` e monta o ZIP portátil.

O cache Hugging Face local (`~/.cache/huggingface/hub`) é a ÚNICA fonte da
verdade: dele saem os hashes/tamanhos do manifesto, os assets da release e a
pasta `models/hub` do ZIP portátil. Assim o instalador (que baixa os modelos)
e o portátil (que já os traz) usam exatamente os mesmos bytes.

Subcomandos:
    manifest   Gera src-tauri/windows/models_manifest.nsh (necessário para o
               hooks.nsi compilar). Deve ser rodado sempre que os modelos
               mudarem.
    assets     Copia os 16 arquivos dos snapshots para dist/release-assets/
               com nomes achatados `<alias>--<arquivo>` + SHA256SUMS.txt,
               prontos para subir na release modelos-v1.
    portable   Monta dist/Transcreve-portatil/ (exe + binaries + models/hub +
               LEIA-ME) e compacta em dist/Transcreve-<versão>-portatil.zip.
    all        manifest + assets + portable.

Nada é enviado ao GitHub aqui. Ao final, o script imprime os comandos `gh`
prontos para publicar — a publicação é uma decisão manual.

Uso:
    python scripts/release.py manifest
    python scripts/release.py all
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from functools import cached_property
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
HF_HUB = Path.home() / ".cache" / "huggingface" / "hub"
WINDOWS_DIR = REPO_ROOT / "src-tauri" / "windows"
MANIFEST_NSH = WINDOWS_DIR / "models_manifest.nsh"
DIST_DIR = REPO_ROOT / "dist"
ASSETS_DIR = DIST_DIR / "release-assets"
PORTABLE_DIR = DIST_DIR / "Transcreve-portatil"
TAURI_RELEASE = REPO_ROOT / "src-tauri" / "target" / "release"
TAURI_BINARIES = REPO_ROOT / "src-tauri" / "binaries"

MODELS_RELEASE_TAG = "modelos-v1"

# Limite por arquivo do GitHub Releases. Acima disso, dividimos o ZIP portátil.
GITHUB_ASSET_LIMIT = 2 * 1024**3  # 2 GiB
# Tamanho de cada parte: 2 GiB com folga (evita esbarrar no limite exato).
PART_SIZE = 1900 * 1024**2  # 1,90 GiB

# Cada modelo do cache HF -> alias curto usado nos nomes dos assets da release.
# (org--nome no cache; o alias evita nomes gigantes e some com o `faster-`.)
MODELS: dict[str, str] = {
    "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo": "large-v3-turbo",
    "models--Systran--faster-whisper-small": "small",
    "models--pysentimiento--bertweet-pt-sentiment": "sentiment-pt",
}


class ModelFile:
    """Um arquivo de um snapshot de modelo, com metadados de integridade."""

    def __init__(self, model_dir: str, alias: str, snapshot: str,
                 name: str, path: Path):
        self.model_dir = model_dir      # models--org--nome
        self.alias = alias              # large-v3-turbo
        self.snapshot = snapshot        # hash do snapshot (= refs/main)
        self.name = name                # model.bin
        self.path = path                # caminho absoluto no cache
        self.size = path.stat().st_size

    @cached_property
    def sha256(self) -> str:
        """Hash do arquivo (lê os bytes). Só o `manifest`/`assets` precisam dele;
        `portable` nunca o acessa, então o cálculo (2,5 GB) fica sob demanda."""
        return _sha256(self.path)

    @property
    def asset(self) -> str:
        """Nome achatado do asset na release: `<alias>--<arquivo>`."""
        return f"{self.alias}--{self.name}"

    @property
    def snapdir(self) -> str:
        """Pasta relativa sob hub\\ (usada pelo NSIS, com contrabarras)."""
        return f"{self.model_dir}\\snapshots\\{self.snapshot}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_ref_main(model_dir: Path) -> str:
    ref = model_dir / "refs" / "main"
    if not ref.exists():
        raise SystemExit(
            f"[release] {model_dir.name}: refs/main ausente — modelo incompleto."
        )
    return ref.read_text(encoding="utf-8").strip()


def collect_models() -> list[ModelFile]:
    """Varre o cache HF e devolve os arquivos de todos os modelos esperados.

    A ordem segue MODELS (grande, small, sentiment) e, dentro de cada modelo,
    os arquivos em ordem alfabética — determinístico entre execuções.
    """
    if not HF_HUB.exists():
        raise SystemExit(
            f"[release] cache HF não encontrado em {HF_HUB}.\n"
            f"           Baixe os modelos antes (rode o app em dev uma vez)."
        )

    files: list[ModelFile] = []
    for model_dir_name, alias in MODELS.items():
        model_dir = HF_HUB / model_dir_name
        if not model_dir.is_dir():
            raise SystemExit(
                f"[release] modelo ausente no cache: {model_dir_name}\n"
                f"           esperado em {model_dir}"
            )
        snapshot = _read_ref_main(model_dir)
        snap_dir = model_dir / "snapshots" / snapshot
        if not snap_dir.is_dir():
            raise SystemExit(
                f"[release] snapshot {snapshot} ausente em {snap_dir}"
            )
        # Só arquivos reais do snapshot (o HF usa symlinks p/ blobs; resolvemos
        # via stat/leitura normalmente — iterdir traz os links já resolvidos).
        for entry in sorted(snap_dir.iterdir(), key=lambda p: p.name):
            if entry.is_file() or entry.is_symlink():
                files.append(
                    ModelFile(model_dir_name, alias, snapshot, entry.name,
                              entry.resolve() if entry.is_symlink() else entry)
                )
    return files


def models_in_order(files: list[ModelFile]) -> Iterator[ModelFile]:
    """Um `ModelFile` por modelo (o primeiro de cada `model_dir`), na ordem de
    `files`. Serve às operações "uma vez por modelo" (cabeçalhos, refs/main)."""
    seen: set[str] = set()
    for mf in files:
        if mf.model_dir not in seen:
            seen.add(mf.model_dir)
            yield mf


# ---------------------------------------------------------------------------
#  manifest
# ---------------------------------------------------------------------------
def cmd_manifest(files: list[ModelFile]) -> None:
    """Gera models_manifest.nsh com as macros TC_MODELS_FILES / TC_MODELS_REFS."""
    lines: list[str] = []
    lines.append("; ==========================================================================")
    lines.append("; GERADO por scripts/release.py — NÃO EDITE À MÃO.")
    lines.append("; Lista de arquivos dos modelos (baixados pelo instalador) e os refs/main.")
    lines.append("; Fonte: cache Hugging Face local (~/.cache/huggingface/hub).")
    lines.append(f"; Release dos modelos: {MODELS_RELEASE_TAG}")
    lines.append("; ==========================================================================")
    lines.append("")
    lines.append("; Baixa/verifica cada arquivo. Assinatura:")
    lines.append(";   TC_FETCH_FILE SNAPDIR FILENAME ASSET SIZE SHA256")
    lines.append("!macro TC_MODELS_FILES")

    current_model = None
    for mf in files:
        if mf.model_dir != current_model:
            current_model = mf.model_dir
            lines.append(f"  ; --- {mf.alias} ({mf.model_dir}) ---")
        lines.append(
            f'  !insertmacro TC_FETCH_FILE '
            f'"{mf.snapdir}" "{mf.name}" "{mf.asset}" {mf.size} "{mf.sha256}"'
        )
    lines.append("!macroend")
    lines.append("")
    lines.append("; Grava refs\\main de cada modelo (resolução offline do 'main').")
    lines.append(";   TC_WRITE_REF MODELDIR HASH")
    lines.append("!macro TC_MODELS_REFS")
    models = list(models_in_order(files))
    for mf in models:
        lines.append(f'  !insertmacro TC_WRITE_REF "{mf.model_dir}" "{mf.snapshot}"')
    lines.append("!macroend")
    lines.append("")

    MANIFEST_NSH.write_text("\r\n".join(lines), encoding="utf-8")
    total = sum(mf.size for mf in files)
    print(f"[release] manifesto escrito: {MANIFEST_NSH}")
    print(f"[release]   {len(files)} arquivos, {len(models)} modelos, "
          f"{total / 1e9:.2f} GB no total")


# ---------------------------------------------------------------------------
#  assets
# ---------------------------------------------------------------------------
def cmd_assets(files: list[ModelFile]) -> None:
    """Copia os arquivos achatados para dist/release-assets/ + SHA256SUMS.txt."""
    _purge_dir(ASSETS_DIR)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    sums: list[str] = []
    for mf in files:
        dest = ASSETS_DIR / mf.asset
        print(f"[release] asset {mf.asset} ({mf.size / 1e6:.1f} MB)…")
        shutil.copy2(mf.path, dest)
        sums.append(f"{mf.sha256}  {mf.asset}")
    (ASSETS_DIR / "SHA256SUMS.txt").write_text(
        "\n".join(sums) + "\n", encoding="utf-8"
    )
    print(f"[release] {len(files)} assets em {ASSETS_DIR}")
    print(f"[release] para publicar (só quando você decidir):")
    print(f'    gh release create {MODELS_RELEASE_TAG} '
          f'"{ASSETS_DIR}"/* \\')
    print(f'      --title "Modelos de IA do Transcreve (v1)" \\')
    print(f'      --notes "Modelos usados pelo instalador. Baixados uma única '
          f'vez durante a instalação."')
    print(f"[release] (se a release já existir, use: "
          f'gh release upload {MODELS_RELEASE_TAG} "{ASSETS_DIR}"/* --clobber)')


# ---------------------------------------------------------------------------
#  portable
# ---------------------------------------------------------------------------
LEIA_ME = """\
Transcreve — versão portátil
============================

Transcrição e análise de áudios 100% no seu computador. Nada é enviado para a
internet: os áudios, as transcrições e os modelos de IA ficam todos aqui.

COMO USAR
---------
1. Extraia esta pasta inteira para onde quiser (ex.: sua Área de Trabalho ou
   um pen drive). Mantenha os arquivos juntos — não separe o Transcreve.exe da
   pasta "models".
2. Dê dois cliques em "Transcreve.exe".
   (Na primeira vez, o Windows pode pedir confirmação; é normal para programas
    novos sem assinatura paga.)

ONDE FICAM OS SEUS DADOS
------------------------
Nesta versão portátil, tudo fica DENTRO desta pasta:
  - models\\  -> os modelos de inteligência artificial (~2,5 GB)
  - data\\    -> seus projetos, transcrições e áudios (criada no primeiro uso)
Para fazer backup ou levar para outro computador, basta copiar a pasta toda.

ATUALIZAR
---------
Baixe a nova versão portátil e substitua o Transcreve.exe e a pasta "binaries".
Você pode manter as pastas "models" e "data" para não baixar tudo de novo.

Projeto: https://github.com/Hebert-Almeida/transcreve
Licença: GPL-3.0
"""


def _app_version() -> str:
    """Lê a versão do tauri.conf.json (para nomear o zip)."""
    import json
    conf = REPO_ROOT / "src-tauri" / "tauri.conf.json"
    try:
        data = json.loads(conf.read_text(encoding="utf-8"))
        return data.get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def _find_app_exe() -> Path:
    """Localiza o executável do app compilado em target/release."""
    # O nome vem do productName/binary do Tauri; procuramos o .exe mais provável.
    candidates = [
        TAURI_RELEASE / "Transcreve.exe",
        TAURI_RELEASE / "transcreve.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    # fallback: primeiro .exe na raiz de target/release (ignora deps/build)
    if TAURI_RELEASE.is_dir():
        for exe in sorted(TAURI_RELEASE.glob("*.exe")):
            return exe
    raise SystemExit(
        f"[release] app não compilado: nenhum .exe em {TAURI_RELEASE}.\n"
        f"           Rode antes: npm run tauri build"
    )


def _robocopy_mirror(src: Path, dst: Path) -> None:
    """Espelha src->dst com robocopy (lida com caminhos > 260 chars)."""
    dst.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["robocopy", str(src), str(dst), "/MIR",
         "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP"],
    )
    if result.returncode >= 8:
        raise SystemExit(f"[release] robocopy falhou ({src} -> {dst}, "
                         f"código {result.returncode})")


def cmd_portable(files: list[ModelFile]) -> None:
    """Monta a pasta portátil e a compacta em um único .zip (ZIP64)."""
    app_exe = _find_app_exe()
    if not TAURI_BINARIES.is_dir():
        raise SystemExit(
            f"[release] {TAURI_BINARIES} não existe — rode o build do sidecar "
            f"(sidecar/.venv312/Scripts/python build.py)."
        )

    print(f"[release] limpando {PORTABLE_DIR}…")
    _purge_dir(PORTABLE_DIR)
    PORTABLE_DIR.mkdir(parents=True, exist_ok=True)

    # 1) executável do app (nome fixo Transcreve.exe para o LEIA-ME bater)
    shutil.copy2(app_exe, PORTABLE_DIR / "Transcreve.exe")
    print(f"[release] app: {app_exe.name} -> Transcreve.exe")

    # 2) sidecar + _internal (a pasta binaries inteira)
    print(f"[release] binaries -> {PORTABLE_DIR / 'binaries'} (robocopy)…")
    _robocopy_mirror(TAURI_BINARIES, PORTABLE_DIR / "binaries")

    # 3) modelos no layout HF (refs/main + snapshots), montados a partir do
    #    cache — replicamos só o necessário, na estrutura que o runtime espera:
    #    models\hub\models--...\{refs\main, snapshots\<hash>\<arquivos>}
    hub = PORTABLE_DIR / "models" / "hub"
    for mf in files:
        dest = hub / mf.snapdir / mf.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mf.path, dest)
    for mf in models_in_order(files):
        ref = hub / mf.model_dir / "refs" / "main"
        ref.parent.mkdir(parents=True, exist_ok=True)
        ref.write_text(mf.snapshot, encoding="utf-8")
    total = sum(mf.size for mf in files)
    print(f"[release] modelos -> {hub} ({total / 1e9:.2f} GB, "
          f"{len(files)} arquivos)")

    # 4) LEIA-ME
    (PORTABLE_DIR / "LEIA-ME.txt").write_text(LEIA_ME, encoding="utf-8")

    # 5) zip (ZIP64 obrigatório: passa de 2 GiB e de 65k arquivos não, mas o
    #    tamanho sim). A pasta-topo dentro do zip é "Transcreve/".
    version = _app_version()
    zip_path = DIST_DIR / f"Transcreve-{version}-portatil.zip"
    if zip_path.exists():
        zip_path.unlink()
    print(f"[release] compactando -> {zip_path} (pode demorar)…")
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED,
        compresslevel=6, allowZip64=True,
    ) as zf:
        for path in sorted(PORTABLE_DIR.rglob("*")):
            if path.is_file():
                arcname = Path("Transcreve") / path.relative_to(PORTABLE_DIR)
                zf.write(path, arcname.as_posix())
    zip_size = zip_path.stat().st_size
    print(f"[release] ZIP pronto: {zip_path} ({zip_size / 1e9:.2f} GB)")

    # 6) O ZIP passa de 2 GiB (limite por arquivo do GitHub Releases). Dividimos
    #    em partes < 2 GiB (.zip.001, .zip.002, …) para caber na própria release.
    #    O usuário rejunta com `copy /b` (nativo do Windows) antes de extrair.
    if zip_size < GITHUB_ASSET_LIMIT:
        print("[release] cabe no limite de 2 GiB do GitHub — anexe o .zip direto.")
        return

    parts = _split_file(zip_path, PART_SIZE)
    print(f"[release] ZIP dividido em {len(parts)} partes (< 2 GiB cada):")
    for p in parts:
        print(f"[release]   {p.name}  ({p.stat().st_size / 1e9:.2f} GB)")
    # O ZIP inteiro não precisa mais existir em disco (as partes o reconstroem).
    zip_path.unlink()

    part_glob = f'"dist/{zip_path.stem}.zip."*'
    joined = f"{zip_path.stem}.zip"
    print("[release] para publicar as partes na release da app (quando decidir):")
    print(f'    gh release upload v{version} {part_glob} --clobber')
    print("[release] NAS NOTAS DA RELEASE, explique como juntar (Windows):")
    print(f'    copy /b {joined}.001 + {joined}.002 {joined}')
    print("[release]   e então extrair o "
          f"{joined} normalmente.")


def _split_file(path: Path, part_size: int) -> list[Path]:
    """Divide `path` em partes de até `part_size` bytes: .001, .002, …

    As partes são concatenáveis de volta ao arquivo original (bytes crus, sem
    cabeçalho), então o usuário rejunta com `copy /b a.001 + a.002 a` no Windows
    (ou `cat a.* > a` em Unix). Remove partes antigas antes de gerar as novas.
    """
    for old in path.parent.glob(f"{path.name}.[0-9][0-9][0-9]"):
        old.unlink()
    parts: list[Path] = []
    with path.open("rb") as src:
        index = 1
        while True:
            chunk = src.read(part_size)
            if not chunk:
                break
            part = path.with_name(f"{path.name}.{index:03d}")
            part.write_bytes(chunk)
            parts.append(part)
            index += 1
    return parts


def _purge_dir(target: Path) -> None:
    """Apaga `target` mesmo com caminhos > 260 chars (espelha um dir vazio)."""
    if not target.exists():
        return
    empty = DIST_DIR / "_empty_purge"
    empty.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["robocopy", str(empty), str(target), "/MIR",
         "/NFL", "/NDL", "/NJH", "/NJS", "/NC", "/NS", "/NP"],
    )
    shutil.rmtree(target, ignore_errors=True)
    shutil.rmtree(empty, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ferramentas de release do Transcreve.")
    parser.add_argument(
        "command",
        choices=["manifest", "assets", "portable", "all"],
        help="manifest: gera o .nsh; assets: prepara arquivos da release; "
             "portable: monta o zip; all: tudo.",
    )
    args = parser.parse_args()

    files = collect_models()

    if args.command in ("manifest", "all"):
        cmd_manifest(files)
    if args.command in ("assets", "all"):
        cmd_assets(files)
    if args.command in ("portable", "all"):
        cmd_portable(files)


if __name__ == "__main__":
    main()
