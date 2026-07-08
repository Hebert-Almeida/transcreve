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
- 🔒 **Confidencial por design** — o áudio nunca sai da máquina; funciona 100% offline depois
  que os modelos de IA estão no computador (baixados uma única vez na instalação, ou já
  incluídos na versão portátil).
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

Há **duas formas** de usar o Transcreve. Escolha a que preferir:

| | **Instalador** | **Versão portátil (ZIP)** |
|---|---|---|
| Como funciona | Instala no computador, cria atalhos | Extrair e usar; não instala nada |
| Modelos de IA (~2,5 GB) | **Baixados durante a instalação** (precisa de internet só nessa hora) | **Já vêm dentro do ZIP** (não baixa nada) |
| Precisa de administrador | Sim (instala para todos os usuários) | Não |
| Tamanho do download | Instalador pequeno + ~2,5 GB de modelos | ZIP único de ~2,5 GB |
| Ideal para | Uso no seu próprio computador | Pen drive, computador compartilhado, sem internet no local |

### Opção A — Instalador

1. Acesse a página de [Releases](../../releases) deste repositório.
2. Na versão mais recente, baixe o arquivo `Transcreve_<versão>_x64-setup.exe`
   (o `<versão>` é o número da versão, por exemplo `0.1.0`).
3. Dê dois cliques no arquivo para iniciar a instalação.
   - O Windows pode mostrar um aviso de segurança (comum em programas novos sem assinatura
     digital paga). Se aparecer, clique em "Mais informações" e depois em "Executar assim mesmo".
   - O instalador pede permissão de administrador — é necessário porque o programa é
     instalado para todos os usuários. Clique em "Sim".
4. **Durante a instalação, o instalador baixa os modelos de inteligência artificial
   (cerca de 2,5 GB) e explica na tela por que está fazendo isso.** Esses arquivos são
   grandes demais para caber no instalador, então são baixados uma única vez, da própria
   página oficial do projeto no GitHub. Uma barra de progresso mostra o andamento.
   - **Precisa estar conectado à internet nessa etapa.** Se preferir deixar para depois, ou
     se a conexão cair, é só executar o instalador novamente mais tarde — o download continua
     de onde parou.
5. Abra o Transcreve pelo atalho criado na área de trabalho ou no menu Iniciar.
6. Pronto! A partir daí o Transcreve funciona **totalmente offline**.

> **Atualizar não baixa os 2,5 GB de novo.** Ao instalar uma versão mais nova por cima, o
> instalador percebe que os modelos já estão no computador e pula o download.

### Opção B — Versão portátil (ZIP)

Como o pacote portátil é grande (~2,5 GB), ele é publicado em **duas partes**
(`...portatil.zip.001` e `...portatil.zip.002`). É preciso juntá-las uma única vez:

1. Baixe **todas as partes** (`Transcreve-<versão>-portatil.zip.001` e `.002`) para a
   mesma pasta.
2. Junte as partes num arquivo só. No Windows, sem instalar nada: abra a pasta onde elas
   estão, clique na barra de endereço, digite `cmd` e Enter; na janela preta, cole:
   ```bat
   copy /b Transcreve-0.1.0-portatil.zip.001 + Transcreve-0.1.0-portatil.zip.002 Transcreve-0.1.0-portatil.zip
   ```
   (troque `0.1.0` pela versão que você baixou). Isso cria o `Transcreve-<versão>-portatil.zip`.
3. Clique com o botão direito nesse `.zip` → "Extrair tudo" e escolha um lugar (pode ser a
   Área de Trabalho ou um pen drive). **Mantenha os arquivos juntos** — não separe o
   `Transcreve.exe` da pasta `models`.
4. Entre na pasta extraída e dê dois cliques em `Transcreve.exe`. (Na primeira vez o Windows
   pode pedir confirmação, como em qualquer programa novo sem assinatura paga.)
5. Pronto — funciona **offline desde o primeiro uso**, sem baixar mais nada.

### Onde ficam os seus arquivos

- **Instalador:** os dados que você cria (banco de dados, transcrições, áudios) ficam em
  `%LOCALAPPDATA%\Transcreve\data` (na sua conta de usuário). Os modelos de IA ficam em
  `C:\ProgramData\Transcreve\models` (compartilhados por todos os usuários). Assim,
  desinstalar ou reinstalar o programa não apaga o seu trabalho.
- **Versão portátil:** tudo fica **dentro da própria pasta** que você extraiu — os modelos em
  `models\` e o seu trabalho em `data\`. Para backup ou para levar a outro computador, basta
  copiar a pasta inteira.

### Vou precisar de internet para usar o programa?

Só uma vez, e só na Opção A: o instalador baixa os modelos durante a instalação. Depois disso
(ou desde o começo, se você usar a versão portátil) o Transcreve funciona **sem internet**.
Nenhum áudio ou dado seu é enviado para fora do computador em momento algum.

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

Não há CI ainda — o processo é local. São dois artefatos (instalador e ZIP portátil) e uma
release fixa só com os modelos.

### Entrega dos modelos, em resumo

Os modelos de IA (~2,5 GB) **não entram** no instalador (o NSIS usa `mmap` e falha perto de
2 GB) nem no bundle do sidecar. Eles ficam numa release à parte, `modelos-v1`, como 16
arquivos soltos:

- O **instalador** baixa esses arquivos durante a instalação, para
  `C:\ProgramData\Transcreve\models`, e confere o SHA-256 de cada um. Atualizações pulam o
  download (os arquivos já existem com o tamanho certo).
- A **versão portátil** já traz os mesmos arquivos dentro de `models\hub\`.

Os hashes/tamanhos ficam em `src-tauri/windows/models_manifest.nsh`, **gerado** por
`scripts/release.py` a partir do cache Hugging Face local — não edite à mão.

### Passo a passo

```bash
# 0) Uma vez: garanta os 3 modelos no cache HF do usuário (~/.cache/huggingface/hub).
#    Rodar o app em dev (npm run tauri dev) e transcrever um áudio curto já baixa tudo.

# 1) Gere o manifesto NSIS dos modelos (necessário para o instalador compilar):
python scripts/release.py manifest

# 2) Congele o sidecar com PyInstaller e espelhe para src-tauri/binaries/:
cd sidecar
python build.py
cd ..

# 3) Gere o instalador Windows (NSIS). É aqui que os ganchos que baixam os modelos
#    são compilados; o manifesto do passo 1 precisa existir.
npm install
npm run tauri build

# 4) Monte a versão portátil (exe + binaries + models/hub + LEIA-ME) num único .zip,
#    e prepare os 16 arquivos da release de modelos:
python scripts/release.py all
```

Saídas:

- Instalador: `src-tauri/target/release/bundle/nsis/Transcreve_<versão>_x64-setup.exe`.
- Portátil: `dist/Transcreve-<versão>-portatil.zip`.
- Arquivos dos modelos: `dist/release-assets/` (+ `SHA256SUMS.txt`).

A `<versão>` vem de `version` no `package.json` / `tauri.conf.json`.

## 🚀 Como publicar as releases no GitHub

São **duas** releases: a dos modelos (só na primeira vez, ou quando os modelos mudarem) e a
da aplicação (a cada versão). Publique com a [GitHub CLI](https://cli.github.com/)
(`gh auth login` uma vez).

**1) Release dos modelos** (`modelos-v1`) — a URL fixa de onde o instalador baixa. Só precisa
existir uma vez; não mude a tag sem também atualizar `TC_MODELS_URL` no
`src-tauri/windows/hooks.nsi`. O comando exato é impresso por `python scripts/release.py assets`:

```bash
gh release create modelos-v1 "dist/release-assets/"* \
  --title "Modelos de IA do Transcreve (v1)" \
  --notes "Modelos usados pelo instalador. Baixados uma única vez durante a instalação."
```

**2) Release da aplicação** (ex.: `v0.1.0`) — o instalador e o ZIP portátil:

```bash
# Cria a release já com o instalador:
gh release create v0.1.0 \
  "src-tauri/target/release/bundle/nsis/Transcreve_0.1.0_x64-setup.exe" \
  --title "Transcreve v0.1.0" \
  --notes "Descreva aqui as novidades desta versão."
```

**ZIP portátil em partes.** O ZIP passa de 2 GiB, que é o limite por arquivo do GitHub
Releases. Por isso o `python scripts/release.py portable` já o divide em partes < 2 GiB
(`Transcreve-<versão>-portatil.zip.001`, `.002`, …) em `dist/`. Anexe as partes à mesma
release (o comando exato é impresso pelo script):

```bash
gh release upload v0.1.0 "dist/Transcreve-0.1.0-portatil.zip."* --clobber
```

E **nas notas da release**, explique ao usuário como juntar as partes antes de extrair
(no Windows, sem instalar nada):

```bat
copy /b Transcreve-0.1.0-portatil.zip.001 + Transcreve-0.1.0-portatil.zip.002 Transcreve-0.1.0-portatil.zip
```

Depois é só extrair o `.zip` resultante normalmente.

Mantenha a tag (`v0.1.0`), o título e a `version` do projeto em sincronia a cada release.

## 📄 Licença

[GPL-3.0](LICENSE) © 2026 Hebert Almeida

Software livre sob a GNU General Public License v3.0 — qualquer trabalho derivado
também deve permanecer aberto sob a mesma licença.
