//! Gerência do sidecar Python (FastAPI).
//!
//! Em desenvolvimento, executa o interpretador do venv (`sidecar/.venv312`).
//! Em produção, executa o binário embarcado via `externalBin` (PyInstaller).
//!
//! O Rust reserva uma porta livre e injeta `TRANSCREVE_PORT` e
//! `TRANSCREVE_DATA_DIR` no ambiente do sidecar; a porta é devolvida ao
//! frontend pelo comando `sidecar_port`. O processo é encerrado junto com o
//! app para não deixar órfãos.

use std::net::TcpListener;
use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Porta usada quando não foi possível reservar uma livre (espelha o padrão do
/// `app.py`). Em condições normais a porta é dinâmica — ver [`pick_free_port`].
pub const DEFAULT_PORT: u16 = 8756;

/// Guarda o processo filho para podermos encerrá-lo no shutdown.
#[derive(Default)]
pub struct SidecarState(pub Mutex<Option<CommandChild>>);

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

/// Diretório de dados do app (`app_data_dir`), passado ao sidecar para que o
/// banco e os áudios caiam na pasta canônica por SO, não no APPDATA cru.
fn data_dir(app: &tauri::AppHandle) -> Option<String> {
    app.path()
        .app_data_dir()
        .ok()
        .map(|p| p.to_string_lossy().into_owned())
}

/// Monta o `Command` apropriado para dev (venv) ou produção (binário embarcado),
/// injetando a porta e o diretório de dados via variáveis de ambiente.
fn build_command(
    app: &tauri::AppHandle,
    port: u16,
) -> Result<tauri_plugin_shell::process::Command, String> {
    let command = if cfg!(debug_assertions) {
        // Dev: usa o Python do venv. O cwd do `tauri dev` é `src-tauri`,
        // então `../sidecar` aponta para a pasta do sidecar.
        // Usa a venv 3.12 (`.venv312`): o pysentimiento (torch/transformers)
        // não tem wheels para 3.14, e ela já tem todo o stack do sidecar.
        let python = if cfg!(windows) {
            "../sidecar/.venv312/Scripts/python.exe"
        } else {
            "../sidecar/.venv312/bin/python"
        };
        app.shell()
            .command(python)
            .args(["app.py"])
            .current_dir(std::path::PathBuf::from("../sidecar"))
    } else {
        // Produção: binário embarcado (resolvido pelo nome, sem caminho).
        app.shell()
            .sidecar("transcreve-sidecar")
            .map_err(|e| e.to_string())?
    };

    let mut command = command.env("TRANSCREVE_PORT", port.to_string());
    if let Some(dir) = data_dir(app) {
        command = command.env("TRANSCREVE_DATA_DIR", dir);
    }
    Ok(command)
}

/// Sobe o sidecar e registra o processo no estado da aplicação.
pub fn spawn(app: &tauri::AppHandle) {
    let port = pick_free_port();
    *app.state::<SidecarPort>().0.lock().unwrap() = port;

    let command = match build_command(app, port) {
        Ok(c) => c,
        Err(err) => {
            eprintln!("[sidecar] não foi possível montar o comando: {err}");
            return;
        }
    };

    match command.spawn() {
        Ok((mut rx, child)) => {
            let state = app.state::<SidecarState>();
            *state.0.lock().unwrap() = Some(child);

            let app_handle = app.clone();
            // Encaminha logs do sidecar para o console do app (útil em dev).
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => log_line("sidecar:out", &line),
                        CommandEvent::Stderr(line) => log_line("sidecar:err", &line),
                        CommandEvent::Terminated(payload) => {
                            eprintln!("[sidecar] encerrado: {:?}", payload.code);
                            let state = app_handle.state::<SidecarState>();
                            *state.0.lock().unwrap() = None;
                        }
                        _ => {}
                    }
                }
            });
        }
        Err(err) => eprintln!("[sidecar] falha ao iniciar: {err}"),
    }
}

fn log_line(tag: &str, bytes: &[u8]) {
    let text = String::from_utf8_lossy(bytes);
    let text = text.trim_end();
    if !text.is_empty() {
        println!("[{tag}] {text}");
    }
}

/// Encerra o sidecar (chamado no evento de saída do app).
pub fn shutdown(app: &tauri::AppHandle) {
    let state = app.state::<SidecarState>();
    // Tira o processo do Mutex e solta o lock antes de matá-lo.
    let child = state.0.lock().unwrap().take();
    if let Some(child) = child {
        let _ = child.kill();
    }
}

/// Liga o encerramento do sidecar ao ciclo de vida da aplicação.
pub fn handle_run_event(app: &tauri::AppHandle, event: &RunEvent) {
    if let RunEvent::ExitRequested { .. } = event {
        shutdown(app);
    }
}
