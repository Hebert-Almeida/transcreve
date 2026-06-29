//! Gerência do sidecar Python (FastAPI).
//!
//! Em desenvolvimento, executa o interpretador do venv (`sidecar/.venv`).
//! Em produção, executa o binário embarcado via `externalBin` (PyInstaller).
//!
//! O processo é encerrado junto com o app para não deixar órfãos.

use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Porta fixa onde o sidecar escuta (espelha `app.py`).
pub const SIDECAR_PORT: u16 = 8756;

/// Guarda o processo filho para podermos encerrá-lo no shutdown.
#[derive(Default)]
pub struct SidecarState(pub Mutex<Option<CommandChild>>);

/// Monta o `Command` apropriado para dev (venv) ou produção (binário embarcado).
fn build_command(
    app: &tauri::AppHandle,
) -> Result<tauri_plugin_shell::process::Command, String> {
    if cfg!(debug_assertions) {
        // Dev: usa o Python do venv. O cwd do `tauri dev` é `src-tauri`,
        // então `../sidecar` aponta para a pasta do sidecar.
        let python = if cfg!(windows) {
            "../sidecar/.venv/Scripts/python.exe"
        } else {
            "../sidecar/.venv/bin/python"
        };
        Ok(app
            .shell()
            .command(python)
            .args(["app.py"])
            .current_dir(std::path::PathBuf::from("../sidecar")))
    } else {
        // Produção: binário embarcado (resolvido pelo nome, sem caminho).
        app.shell()
            .sidecar("transcreve-sidecar")
            .map_err(|e| e.to_string())
    }
}

/// Sobe o sidecar e registra o processo no estado da aplicação.
pub fn spawn(app: &tauri::AppHandle) {
    let command = match build_command(app) {
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
