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

Por enquanto, o Transcreve só tem instalador pronto para **Windows, versão 64 bits**
Não existe versão para Windows de 32 bits, nem instalador pronto para macOS ou Linux ainda.
O código foi feito para funcionar nesses sistemas no futuro, mas isso ainda não foi testado
nem publicado — por enquanto, quem usa Mac ou Linux só consegue rodar o projeto "pelo código-fonte"
(seção de desenvolvimento mais abaixo), o que exige mais conhecimento técnico.

## 📦 Status

🚧 **Em desenvolvimento inicial** (`v0.1.0`) — funcional ponta a ponta (transcrição, análise
qualitativa e quantitativa, exportação), mas ainda sem diarização de falantes.

## 💾 Como instalar (Windows)

Se você não sabe se seu Windows é 32 ou 64 bits: aperte a tecla Windows, digite
"Informações do sistema" e abra o programa. Procure o campo "Tipo de sistema" — se aparecer
"x64", seu computador é compatível.

1. Acesse a página de [Releases](../../releases) deste repositório (é a página onde ficam
   as versões prontas para baixar).
2. Na versão mais recente, clique para baixar o arquivo chamado
   `Transcreve_<versão>_x64-setup.exe` (o `<versão>` é o número da versão, por exemplo `0.1.0`).
3. Depois de baixado, dê dois cliques no arquivo para iniciar a instalação.
   - O Windows pode mostrar um aviso de segurança (comum em programas novos e menos
     conhecidos). Se aparecer, clique em "Mais informações" e depois em "Executar assim mesmo".
   - O instalador vai pedir permissão de administrador — isso é necessário porque o programa
     é instalado para todos os usuários do computador. Clique em "Sim".
   - Escolha a pasta onde deseja instalar (ou apenas aceite a pasta sugerida) e siga as
     instruções na tela até o fim.
4. Abra o Transcreve pelo atalho que foi criado na área de trabalho ou no menu Iniciar.
5. Na primeira vez que abrir, o programa vai copiar os modelos de inteligência artificial
   (cerca de 2,5 GB) para a pasta de dados dele. Isso pode demorar alguns minutos, mas só
   acontece uma vez e **não precisa de internet** (os modelos já vêm dentro do instalador).
6. Pronto! Depois desse primeiro passo, o Transcreve funciona **totalmente offline** — ou
   seja, sem precisar estar conectado à internet.

Os arquivos que o programa cria (banco de dados, áudios, modelos) ficam guardados na pasta
`data`, ao lado de onde o programa foi instalado.

### Vou precisar de internet para usar o programa?

Não. Depois da primeira abertura (que copia os modelos), o Transcreve funciona sem internet.
Nenhum áudio ou dado seu é enviado para fora do computador.

### macOS e Linux

Ainda não existe um instalador pronto (tipo `.dmg` ou `.AppImage`) para macOS ou Linux. Se
você usa um desses sistemas e quer experimentar o Transcreve, será necessário compilar o
programa a partir do código-fonte — veja a seção "Desenvolvimento" logo abaixo. Esse caminho
exige instalar ferramentas de programação (Node.js, Rust, Python) e é recomendado apenas
para quem já tem alguma familiaridade com terminal/linha de comando.

### O que meu computador precisa ter

- Windows 10 ou 11, versão de 64 bits.
- Cerca de 4 GB de espaço livre no disco (para o programa e os modelos de IA).
- Uma placa de vídeo NVIDIA é opcional — ela deixa a transcrição mais rápida, mas o programa
  funciona normalmente sem ela, apenas usando o processador (nesse caso, em computadores com
  pouca memória RAM, ele escolhe automaticamente um modelo de IA mais leve).

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
