/// Starts the native JARVIS desktop shell.
///
/// Native commands and plugins are intentionally not registered yet. Each future
/// capability must be reviewed, permission-scoped, and covered by tests before
/// it is exposed to the webview.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("error while running JARVIS desktop application");
}
