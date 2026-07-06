# Transcreve

> Transcrição e análise de áudios de pesquisa — **100% local, offline e confidencial**.

**Transcreve** é uma aplicação desktop open-source que ajuda pesquisadores a transcrever
áudios longos (entrevistas, grupos focais) e a analisá-los qualitativa e quantitativamente,
sem enviar nenhum dado para a nuvem. Pensada para ser doada a universidades, com visual
minimalista, modo claro/escuro e suporte a Português (Brasil), Inglês e Espanhol.

## ✨ Funcionalidades

- 🎙️ **Transcrição local** de áudios longos com [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  (Whisper `large-v3-turbo`, com fallback automático para o modelo `small` em máquinas com
  pouca RAM e sem GPU).
- 🔒 **Confidencial por design** — o áudio nunca sai da máquina; funciona 100% offline após
  a instalação (modelos já vêm embarcados).
- 📊 **Análises quantitativas** — frequência de termos, riqueza lexical, tempo por falante,
  velocidade de fala.
- 🏷️ **Análise qualitativa** — codificação temática, word clouds, co-ocorrência de códigos.
- 😊 **Análise de sentimento** em PT/EN/ES por trecho (via [pysentimiento](https://github.com/pysentimiento/pysentimiento)).
- 📤 **Exportação** para CSV/TSV (RStudio), DOCX/PDF e JSON.
- 🌗 **Visual minimalista** com tema claro e escuro.
- ⚙️ **CPU ou GPU (CUDA)** — detecção automática de hardware, com opção de escolher
  manualmente o device e o modelo em Configurações.

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Shell desktop | [Tauri v2](https://v2.tauri.app/) (Rust) |
| Frontend | SvelteKit + TypeScript + Tailwind CSS |
| Backend de IA (sidecar) | Python + FastAPI + faster-whisper |
| Persistência | SQLite (local) |

A interface roda no WebView nativo do sistema (baixo consumo de RAM) e o trabalho pesado de
IA roda em um processo Python embarcado como _sidecar_ (congelado com PyInstaller),
iniciado e gerenciado automaticamente pelo Tauri.

## 🚀 Plataformas

Atualmente empacotado para **Windows** (instalador NSIS). O código é multiplataforma por
natureza (Tauri + Python), mas builds para macOS/Linux ainda não são publicados.

## 📦 Status

🚧 **Em desenvolvimento inicial** (`v0.1.0`) — funcional ponta a ponta (transcrição, análise
qualitativa e quantitativa, exportação), mas ainda sem diarização de falantes.

## 💾 Instalação (usuário final)

1. Baixe o instalador mais recente (`Transcreve_<versão>_x64-setup.exe`) na página de
   [Releases](../../releases) do repositório.
2. Execute o instalador. Ele pede privilégios de administrador (instalação por máquina) e
   deixa você escolher a pasta de destino.
3. Abra o Transcreve pelo atalho criado. No primeiro início, o app copia os modelos de IA
   (~2,5 GB, já incluídos no instalador) para a pasta de dados — isso acontece uma única vez
   e não requer internet.
4. Pronto — depois disso o app funciona **totalmente offline**.

Os dados do usuário (banco SQLite, áudios, modelos semeados) ficam em `data/`, ao lado do
executável instalado — tudo no mesmo disco escolhido na instalação, sem depender de
`%APPDATA%`.

### Requisitos do sistema

- Windows 10/11 64-bit.
- ~4 GB de espaço em disco livre (app + modelos).
- GPU NVIDIA (CUDA) é opcional — acelera a transcrição, mas o app funciona normalmente em
  CPU (usa automaticamente um modelo menor em máquinas com pouca RAM).

## 🛠️ Desenvolvimento

Pré-requisitos:

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://rustup.rs/) (toolchain estável)
- [Python](https://www.python.org/) 3.12 (usado para o sidecar — o build empacotado exige
  3.12 por causa de dependências como `torch`/`pysentimiento`, que não têm wheels para
  versões mais novas ainda)

### Frontend + shell Tauri

```bash
# instalar dependências do frontend
npm install

# rodar o app completo (frontend + sidecar Python) em modo desenvolvimento
npm run tauri dev
```

Em modo dev o sidecar Python roda direto do código-fonte (sem PyInstaller) e usa o cache do
Hugging Face do próprio usuário (`~/.cache/huggingface/hub`), baixando os modelos sob
demanda na primeira transcrição.

Outros scripts úteis:

```bash
npm run dev      # só o frontend (Vite), sem o shell Tauri
npm run build    # build de produção do frontend (SvelteKit estático)
npm run check    # type-check (svelte-check)
```

### Sidecar Python (standalone)

```bash
cd sidecar
python -m venv .venv312          # crie a venv com Python 3.12
.venv312\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload         # sobe o servidor FastAPI isolado, se precisar depurar
```

## 📦 Como gerar um build de instalação (release)

O sidecar precisa ser "congelado" com PyInstaller *antes* de empacotar o app com o Tauri —
não existe pipeline de CI para isso ainda, o processo é local:

```bash
# 1) Com a venv312 do sidecar ativa e os modelos já baixados no cache HF do usuário:
cd sidecar
python build.py
# Isso roda o PyInstaller (onedir), copia os modelos (~2,5 GB) e espelha tudo para
# src-tauri/binaries/ (embarcado como resource do Tauri).

# 2) Na raiz do projeto, gere o instalador Windows (NSIS):
cd ..
npm install
npm run tauri build
```

O instalador final fica em `src-tauri/target/release/bundle/nsis/` — o arquivo se chama
`Transcreve_<versão>_x64-setup.exe` (a `<versão>` vem de `version` no `package.json` /
`tauri.conf.json`). Como os modelos são semeados no primeiro boot (fora do instalador), o
`.exe` fica enxuto.

## 🚀 Como publicar a release no GitHub

Depois de gerar o instalador acima, publique-o na página de [Releases](../../releases). Os
artefatos são o instalador `.exe` e uma cópia **zipada** dele (mesmo conteúdo, só compactado
para quem prefere baixar `.zip`).

```powershell
# 1) (opcional) Zipar o instalador — use a versão real no nome:
Compress-Archive `
  -Path "src-tauri\target\release\bundle\nsis\Transcreve_0.1.0_x64-setup.exe" `
  -DestinationPath "src-tauri\target\release\bundle\nsis\Transcreve_0.1.0_x64-setup.zip"
```

Depois, publique com a [GitHub CLI](https://cli.github.com/) (`gh auth login` uma vez) —
cria a tag, a release e anexa os dois arquivos de uma vez:

```bash
gh release create v0.1.0 \
  "src-tauri/target/release/bundle/nsis/Transcreve_0.1.0_x64-setup.exe" \
  "src-tauri/target/release/bundle/nsis/Transcreve_0.1.0_x64-setup.zip" \
  --title "Transcreve v0.1.0" \
  --notes "Descreva aqui as novidades desta versão."
```

> Alternativa sem CLI: **Releases → Draft a new release**, crie a tag `v0.1.0`, escreva as
> notas e arraste o `.exe` (e o `.zip`) para a área de anexos. Publique.

Convém manter a tag (`v0.1.0`), o título e a `version` do projeto em sincronia a cada release.

## 📄 Licença

[GPL-3.0](LICENSE) © 2026 Hebert Almeida

Software livre sob a GNU General Public License v3.0 — qualquer trabalho derivado
também deve permanecer aberto sob a mesma licença.
