//! Gerência do sidecar Python (FastAPI).
//!
//! Em desenvolvimento, executa o interpretador do venv (`sidecar/.venv312`).
//! Em produção, executa o binário congelado (PyInstaller onedir) empacotado como
//! `resource` do Tauri: o exe fica em `resources/binaries/` ao lado da pasta
//! `_internal/` (que o PyInstaller exige como irmã). Por isso NÃO usamos o
//! `externalBin`/`.sidecar()` (que empacota um único arquivo) — resolvemos o
//! caminho do exe via `resource_dir()` e o executamos diretamente.
//!
//! O Rust reserva uma porta livre e injeta `TRANSCREVE_PORT` e
//! `TRANSCREVE_DATA_DIR` no ambiente do sidecar; a porta é devolvida ao
//! frontend pelo comando `sidecar_port`. O processo é encerrado junto com o
//! app para não deixar órfãos.

use std::io::{BufRead, BufReader};
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

use tauri::{Manager, RunEvent};

/// Porta usada quando não foi possível reservar uma livre (espelha o padrão do
/// `app.py`). Em condições normais a porta é dinâmica — ver [`pick_free_port`].
pub const DEFAULT_PORT: u16 = 8756;

/// Guarda o processo filho para podermos encerrá-lo no shutdown.
#[derive(Default)]
pub struct SidecarState(pub Mutex<Option<Child>>);

/// Porta efetiva onde o sidecar escuta, resolvida no spawn e devolvida ao
/// frontend via comando. Fica em estado gerenciado para o `sidecar_port` lê-la.
pub struct SidecarPort(pub Mutex<u16>);

impl Default for SidecarPort {
    fn default() -> Self {
        SidecarPort(Mutex::new(DEFAULT_PORT))
    }
}

/// Reserva uma porta livre pedindo a porta 0 ao SO e lendo a que ele atribuiu.
/// O listener é descartado em seguida; resta uma janela mínima (TOCTOU) até o
/// sidecar bindar, aceitável num app local de um usuário só. Fallback ao padrão.
fn pick_free_port() -> u16 {
    TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|addr| addr.port())
        .unwrap_or(DEFAULT_PORT)
}

/// Diretório de dados do app, passado ao sidecar para o banco e os áudios.
///
/// Em produção, os dados ficam AO LADO do app instalado (`<pasta do exe>\data`):
/// assim tudo (programa, modelos e dados do usuário) mora no mesmo disco que o
/// usuário escolheu no instalador — sem prender nada ao C:\...\Roaming. A pasta
/// é gravável e persiste entre execuções; o instalador não a apaga ao remover.
/// Em dev usamos o `app_data_dir` canônico (não há "pasta do exe" instalada).
fn data_dir(app: &tauri::AppHandle) -> Option<String> {
    if !cfg!(debug_assertions) {
        if let Ok(exe) = std::env::current_exe() {
            if let Some(dir) = exe.parent() {
                return Some(dir.join("data").to_string_lossy().into_owned());
            }
        }
    }
    app.path()
        .app_data_dir()
        .ok()
        .map(|p| p.to_string_lossy().into_owned())
}

/// Monta o `Command` apropriado para dev (venv) ou produção (binário congelado),
/// injetando a porta e o diretório de dados via variáveis de ambiente.
fn build_command(app: &tauri::AppHandle, port: u16) -> Result<Command, String> {
    let mut command = if cfg!(debug_assertions) {
        // Dev: usa o Python do venv. O cwd do `tauri dev` é `src-tauri`,
        // então `../sidecar` aponta para a pasta do sidecar.
        // Usa a venv 3.12 (`.venv312`): o pysentimiento (torch/transformers)
        // não tem wheels para 3.14, e ela já tem todo o stack do sidecar.
        let python = if cfg!(windows) {
            "../sidecar/.venv312/Scripts/python.exe"
        } else {
            "../sidecar/.venv312/bin/python"
        };
        let mut c = Command::new(python);
        c.arg("app.py").current_dir("../sidecar");
        c
    } else {
        // Produção: exe congelado empacotado como resource. Resolvemos o caminho
        // sob o resource_dir e executamos diretamente (o _internal/ irmão vai
        // junto no bundle). O cwd é a pasta do exe, garantindo que o PyInstaller
        // localize _internal/ mesmo se algum código usar caminhos relativos.
        let exe = sidecar_exe_path(app)?;
        let dir = exe
            .parent()
            .ok_or_else(|| "caminho do sidecar sem diretório-pai".to_string())?
            .to_path_buf();
        let mut c = Command::new(&exe);
        c.current_dir(dir);
        c
    };

    command
        .env("TRANSCREVE_PORT", port.to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    if let Some(dir) = data_dir(app) {
        command.env("TRANSCREVE_DATA_DIR", dir);
    }
    // Em produção, informa ao sidecar onde está o cache de modelos (2,5 GB) que
    // é entregue AO LADO do app (fora do instalador, por limite de tamanho). O
    // sidecar copia daí para o app-data no 1º boot (ver runtime.py).
    if !cfg!(debug_assertions) {
        if let Some(models) = models_source_dir(app) {
            command.env("TRANSCREVE_MODELS_DIR", models);
        }
    }
    Ok(command)
}

/// Pasta de modelos entregue junto do app instalado (`<resource>/binaries/models`).
/// Não é empacotada no instalador (estoura o teto), então é copiada para lá na
/// distribuição. Se ausente, o sidecar recorre ao que já houver em app-data.
fn models_source_dir(app: &tauri::AppHandle) -> Option<String> {
    let resource_dir = app.path().resource_dir().ok()?;
    let models = resource_dir.join("binaries").join("models");
    Some(models.to_string_lossy().into_owned())
}

/// Caminho do exe congelado dentro dos resources do bundle.
/// Empacotamos `binaries/` (exe + `_internal/`) como resource no tauri.conf.json,
/// então o exe fica em `<resource_dir>/binaries/transcreve-sidecar.exe`.
fn sidecar_exe_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir indisponível: {e}"))?;
    let name = if cfg!(windows) {
        "transcreve-sidecar.exe"
    } else {
        "transcreve-sidecar"
    };
    let exe = resource_dir.join("binaries").join(name);
    if !exe.exists() {
        return Err(format!("sidecar não encontrado em {}", exe.display()));
    }
    Ok(exe)
}

/// Sobe o sidecar e registra o processo no estado da aplicação.
pub fn spawn(app: &tauri::AppHandle) {
    let port = pick_free_port();
    *app.state::<SidecarPort>().0.lock().unwrap() = port;

    let mut command = match build_command(app, port) {
        Ok(c) => c,
        Err(err) => {
            eprintln!("[sidecar] não foi possível montar o comando: {err}");
            return;
        }
    };

    match command.spawn() {
        Ok(mut child) => {
            // Encaminha logs do sidecar para o console do app (útil em dev e p/
            // diagnosticar o bundle). Uma thread por stream, pois são bloqueantes.
            if let Some(out) = child.stdout.take() {
                pump_logs("sidecar:out", out);
            }
            if let Some(err) = child.stderr.take() {
                pump_logs("sidecar:err", err);
            }
            let state = app.state::<SidecarState>();
            *state.0.lock().unwrap() = Some(child);
        }
        Err(err) => eprintln!("[sidecar] falha ao iniciar: {err}"),
    }
}

/// Lê linhas de um stream do filho numa thread dedicada e as ecoa no console.
fn pump_logs<R: std::io::Read + Send + 'static>(tag: &'static str, stream: R) {
    std::thread::spawn(move || {
        let reader = BufReader::new(stream);
        for line in reader.lines() {
            match line {
                Ok(text) if !text.trim().is_empty() => println!("[{tag}] {text}"),
                Ok(_) => {}
                Err(_) => break,
            }
        }
    });
}

/// Encerra o sidecar (chamado no evento de saída do app).
pub fn shutdown(app: &tauri::AppHandle) {
    let state = app.state::<SidecarState>();
    // Tira o processo do Mutex e solta o lock antes de matá-lo.
    let child = state.0.lock().unwrap().take();
    if let Some(mut child) = child {
        let _ = child.kill();
        let _ = child.wait();
    }
}

/// Liga o encerramento do sidecar ao ciclo de vida da aplicação.
pub fn handle_run_event(app: &tauri::AppHandle, event: &RunEvent) {
    if let RunEvent::ExitRequested { .. } = event {
        shutdown(app);
    }
}
