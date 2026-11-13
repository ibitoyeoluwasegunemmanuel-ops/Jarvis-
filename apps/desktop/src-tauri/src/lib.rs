use std::sync::Mutex;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use uuid::Uuid;

struct GatewayRuntime {
    child: Mutex<Option<CommandChild>>,
}

fn new_session_token() -> String {
    format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple())
}

/// Starts the native JARVIS desktop shell and its private gateway sidecar.
///
/// The session token is generated in native code and passed only to the gateway
/// process environment. It is never returned to the webview or logged.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let token = new_session_token();
            let child = match app
                .shell()
                .sidecar("jarvis-gateway")
            {
                Ok(command) => match command
                    .args(["--host", "127.0.0.1", "--port", "8765"])
                    .env("JARVIS_SESSION_TOKEN", token)
                    .set_process_group(true)
                    .kill_on_drop(true)
                    .spawn()
                {
                    Ok((mut events, child)) => {
                        // Drain process output without forwarding it to the webview.
                        tauri::async_runtime::spawn(async move {
                            while let Some(event) = events.recv().await {
                                if matches!(event, CommandEvent::Terminated(_)) {
                                    break;
                                }
                            }
                        });
                        Some(child)
                    }
                    Err(error) => {
                        eprintln!("JARVIS gateway sidecar failed to start: {error}");
                        None
                    }
                },
                Err(error) => {
                    eprintln!("JARVIS gateway sidecar is unavailable: {error}");
                    None
                }
            };

            app.manage(GatewayRuntime {
                child: Mutex::new(child),
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building JARVIS desktop application");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(runtime) = handle.try_state::<GatewayRuntime>() {
                if let Ok(mut child_guard) = runtime.child.lock() {
                    if let Some(child) = child_guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}
