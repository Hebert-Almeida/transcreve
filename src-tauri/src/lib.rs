mod sidecar;

use sidecar::SidecarState;

/// Retorna a porta do sidecar para o frontend montar a URL local.
#[tauri::command]
fn sidecar_port() -> u16 {
    sidecar::SIDECAR_PORT
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(SidecarState::default())
        .invoke_handler(tauri::generate_handler![sidecar_port])
        .setup(|app| {
            sidecar::spawn(app.handle());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            sidecar::handle_run_event(app_handle, &event);
        });
}
