use std::sync::Mutex;
use std::time::Duration;

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use uuid::Uuid;

const GATEWAY_CAPABILITIES_URL: &str =
    "http://127.0.0.1:8765/v1/system/capabilities";

struct GatewayRuntime {
    child: Mutex<Option<CommandChild>>,
    session_token: String,
}

fn new_session_token() -> String {
    format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple())
}

/// Fetches the one approved read-only gateway resource through native HTTP.
///
/// The webview never receives the process session token and cannot choose a URL,
/// method, or request headers. Extend this bridge with separately reviewed,
/// typed commands rather than exposing a generic proxy.
#[tauri::command]
async fn get_gateway_capabilities(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|_| "native_gateway_client_unavailable".to_string())?;

    let response = client
        .get(GATEWAY_CAPABILITIES_URL)
        .header("X-Jarvis-Session", &runtime.session_token)
        .send()
        .await
        .map_err(|_| "gateway_not_ready".to_string())?;

    if !response.status().is_success() {
        return Err(format!(
            "gateway_request_failed_{}",
            response.status().as_u16()
        ));
    }

    response
        .json::<serde_json::Value>()
        .await
        .map_err(|_| "gateway_response_invalid".to_string())
}

/// Starts the native JARVIS desktop shell and its private gateway sidecar.
///
/// The session token is generated in native code, passed only to the gateway
/// process environment, and retained only in native managed state for the
/// fixed typed request bridge above.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![get_gateway_capabilities])
        .setup(|app| {
            let token = new_session_token();
            let child = match app.shell().sidecar("jarvis-gateway") {
                Ok(command) => match command
                    .args(["--host", "127.0.0.1", "--port", "8765"])
                    .env("JARVIS_SESSION_TOKEN", token.clone())
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
                session_token: token,
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
