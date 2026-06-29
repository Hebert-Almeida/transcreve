# Transcreve

> Transcrição e análise de áudios de pesquisa — **100% local, offline e confidencial**.

**Transcreve** é uma aplicação desktop open-source que ajuda pesquisadores a transcrever
áudios longos (entrevistas, grupos focais) e a analisá-los qualitativa e quantitativamente,
sem enviar nenhum dado para a nuvem. Pensada para ser doada a universidades, com visual
minimalista, modo claro/escuro e suporte a Português (Brasil), Inglês e Espanhol.

## ✨ Funcionalidades

- 🎙️ **Transcrição local** de áudios longos com [WhisperX](https://github.com/m-bain/whisperX)
  (Whisper `large-v3-turbo`), com fallback automático em máquinas modestas.
- 👥 **Diarização** — identifica e rotula quem fala.
- 🔒 **Confidencial por design** — o áudio nunca sai da máquina; funciona offline.
- 📊 **Análises quantitativas** — frequência de termos, riqueza lexical, tempo por falante,
  velocidade de fala.
- 🏷️ **Análise qualitativa** — codificação temática, word clouds, co-ocorrência de códigos.
- 😊 **Análise de sentimento** em PT-BR por trecho e por falante.
- 📤 **Exportação** para CSV/TSV (RStudio), DOCX/PDF, JSON e SRT/VTT.
- 🌗 **Visual minimalista** com tema claro e escuro.

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Shell desktop | [Tauri v2](https://v2.tauri.app/) (Rust) |
| Frontend | SvelteKit + TypeScript + Tailwind CSS |
| Backend de IA (sidecar) | Python + FastAPI + WhisperX |
| Persistência | SQLite (local) |

A interface roda no WebView nativo do sistema (baixo consumo de RAM) e o trabalho pesado de
IA roda em um processo Python embarcado como _sidecar_, gerenciado pelo Tauri.

## 🚀 Plataformas

Windows · macOS · Linux

## 📦 Status

🚧 **Em desenvolvimento inicial.** Estrutura sendo montada.

## 🛠️ Desenvolvimento

Pré-requisitos: [Node.js](https://nodejs.org/) 20+, [Rust](https://rustup.rs/),
[Python](https://www.python.org/) 3.12.

```bash
# instalar dependências do frontend
npm install

# rodar em modo desenvolvimento
npm run tauri dev
```

(Instruções completas serão adicionadas conforme o projeto evolui.)

## 📄 Licença

[MIT](LICENSE) © 2026 Hebert Almeida
