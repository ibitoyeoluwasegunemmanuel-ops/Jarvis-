use std::sync::Mutex;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use uuid::Uuid;
use zeroize::Zeroize;

const GATEWAY_BASE_URL: &str = "http://127.0.0.1:8765";
const GATEWAY_CAPABILITIES_PATH: &str = "/v1/system/capabilities";
const GATEWAY_AUTH_STATUS_PATH: &str = "/v1/auth/status";
const GATEWAY_AUTH_SETUP_PATH: &str = "/v1/auth/setup";
const GATEWAY_AUTH_LOGIN_PATH: &str = "/v1/auth/login";
const GATEWAY_AUTH_LOGOUT_PATH: &str = "/v1/auth/logout";
const GATEWAY_PROJECTS_PATH: &str = "/v1/projects";
const GATEWAY_TASKS_PATH: &str = "/v1/tasks";

struct GatewayRuntime {
    child: Mutex<Option<CommandChild>>,
    session_token: String,
    owner_session: Mutex<Option<String>>,
}

#[derive(Serialize)]
struct OwnerPasswordPayload<'a> {
    password: &'a str,
}

#[derive(Deserialize)]
struct OwnerSessionPayload {
    owner_session_token: String,
    #[allow(dead_code)]
    display_name: String,
}

#[derive(Deserialize, Serialize)]
struct OwnerAuthStatus {
    owner_configured: bool,
    setup_required: bool,
    authenticated: bool,
}


#[derive(Deserialize, Serialize)]
struct ProjectRecord {
    id: String,
    name: String,
    description: String,
    status: String,
    created_at: f64,
    updated_at: f64,
}

#[derive(Deserialize, Serialize)]
struct ProjectTaskRecord {
    id: String,
    project_id: String,
    title: String,
    description: String,
    status: String,
    created_at: f64,
    updated_at: f64,
}

#[derive(Deserialize, Serialize)]
struct ProjectActivityRecord {
    id: i64,
    event_type: String,
    entity_type: String,
    entity_id: String,
    details_json: String,
    occurred_at: f64,
}

#[derive(Serialize)]
struct ProjectCreatePayload<'a> {
    name: &'a str,
    description: &'a str,
}

#[derive(Serialize)]
struct ProjectStatusPayload<'a> {
    status: &'a str,
}

#[derive(Serialize)]
struct ProjectTaskCreatePayload<'a> {
    title: &'a str,
    description: &'a str,
}

#[derive(Serialize)]
struct ProjectTaskStatusPayload<'a> {
    status: &'a str,
}

fn valid_workspace_id(value: &str) -> bool {
    value.len() == 32 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn new_session_token() -> String {
    format!("{}{}", Uuid::new_v4().simple(), Uuid::new_v4().simple())
}

fn gateway_client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .map_err(|_| "native_gateway_client_unavailable".to_string())
}

fn gateway_url(path: &str) -> String {
    format!("{GATEWAY_BASE_URL}{path}")
}

fn owner_auth_error(status: reqwest::StatusCode) -> String {
    match status.as_u16() {
        401 => "invalid_owner_credentials".to_string(),
        409 => "owner_setup_or_account_state_conflict".to_string(),
        422 => "password_does_not_meet_security_requirements".to_string(),
        429 => "owner_login_temporarily_locked".to_string(),
        _ => format!("owner_auth_request_failed_{}", status.as_u16()),
    }
}

/// Fetches the one approved read-only gateway resource through native HTTP.
///
/// The webview never receives the process session token and cannot choose a URL,
/// method, or request headers. The optional owner session remains native too.
#[tauri::command]
async fn get_gateway_capabilities(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<serde_json::Value, String> {
    let client = gateway_client()?;
    let mut owner_session = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone();

    let result = async {
        let mut request = client
            .get(gateway_url(GATEWAY_CAPABILITIES_PATH))
            .header("X-Jarvis-Session", &runtime.session_token);

        if let Some(token) = owner_session.as_ref() {
            request = request.header("X-Jarvis-Owner-Session", token);
        }

        let response = request
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
    .await;

    if let Some(token) = owner_session.as_mut() {
        token.zeroize();
    }
    result
}

/// Reads whether first-run setup is needed and whether the native owner session
/// is currently valid. No credential or token is returned to the webview.
#[tauri::command]
async fn get_owner_auth_status(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<OwnerAuthStatus, String> {
    let client = gateway_client()?;
    let mut owner_session = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone();

    let result = async {
        let mut request = client
            .get(gateway_url(GATEWAY_AUTH_STATUS_PATH))
            .header("X-Jarvis-Session", &runtime.session_token);

        if let Some(token) = owner_session.as_ref() {
            request = request.header("X-Jarvis-Owner-Session", token);
        }

        let response = request
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if !response.status().is_success() {
            return Err(format!(
                "owner_status_request_failed_{}",
                response.status().as_u16()
            ));
        }

        response
            .json::<OwnerAuthStatus>()
            .await
            .map_err(|_| "owner_status_response_invalid".to_string())
    }
    .await;

    if let Some(token) = owner_session.as_mut() {
        token.zeroize();
    }
    result
}

/// Sends a password to one fixed authentication endpoint and keeps the issued
/// owner-session token exclusively in native managed state.
async fn submit_owner_password(
    runtime: &GatewayRuntime,
    endpoint: &'static str,
    mut password: String,
) -> Result<(), String> {
    let result = async {
        let client = gateway_client()?;
        let response = client
            .post(gateway_url(endpoint))
            .header("X-Jarvis-Session", &runtime.session_token)
            .json(&OwnerPasswordPayload {
                password: &password,
            })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if !response.status().is_success() {
            return Err(owner_auth_error(response.status()));
        }

        let session = response
            .json::<OwnerSessionPayload>()
            .await
            .map_err(|_| "owner_session_response_invalid".to_string())?;

        let mut owner_session = runtime
            .owner_session
            .lock()
            .map_err(|_| "native_owner_session_unavailable".to_string())?;
        *owner_session = Some(session.owner_session_token);
        Ok(())
    }
    .await;

    password.zeroize();
    result
}

/// Creates the first local owner account. The password is never persisted by
/// the desktop process and the returned session token never crosses into JS.
#[tauri::command]
async fn setup_owner(
    password: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<(), String> {
    submit_owner_password(&runtime, GATEWAY_AUTH_SETUP_PATH, password).await
}

/// Authenticates the local owner and stores the issued session in native memory.
#[tauri::command]
async fn login_owner(
    password: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<(), String> {
    submit_owner_password(&runtime, GATEWAY_AUTH_LOGIN_PATH, password).await
}

/// Revokes the native owner session and clears it from process memory.
#[tauri::command]
async fn logout_owner(runtime: tauri::State<'_, GatewayRuntime>) -> Result<(), String> {
    let owner_session = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .take();

    let Some(mut token) = owner_session else {
        return Ok(());
    };

    let result = async {
        let client = gateway_client()?;
        let response = client
            .post(gateway_url(GATEWAY_AUTH_LOGOUT_PATH))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &token)
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if !response.status().is_success() {
            return Err(format!(
                "owner_logout_failed_{}",
                response.status().as_u16()
            ));
        }
        Ok(())
    }
    .await;

    token.zeroize();
    result
}


/// Lists projects through the authenticated native bridge. The owner token is
/// required and is attached in Rust; it is never sent to the webview.
#[tauri::command]
async fn list_projects(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<Vec<ProjectRecord>, String> {
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let response = client
            .get(gateway_url(GATEWAY_PROJECTS_PATH))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_list_failed_{}", response.status().as_u16()));
        }

        response
            .json::<Vec<ProjectRecord>>()
            .await
            .map_err(|_| "project_list_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Creates a local project for the signed-in owner. The owner identity is
/// resolved by the gateway from the native session, never from JS arguments.
#[tauri::command]
async fn create_project(
    name: String,
    description: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectRecord, String> {
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let response = client
            .post(gateway_url(GATEWAY_PROJECTS_PATH))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectCreatePayload {
                name: &name,
                description: &description,
            })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::UNPROCESSABLE_ENTITY {
            return Err("project_details_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_create_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectRecord>()
            .await
            .map_err(|_| "project_create_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}



/// Lists tasks for one validated project. Project ownership is enforced by the gateway.
#[tauri::command]
async fn list_project_tasks(
    project_id: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<Vec<ProjectTaskRecord>, String> {
    if !valid_workspace_id(&project_id) {
        return Err("project_id_invalid".to_string());
    }
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let url = format!("{}/{project_id}/tasks", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client
            .get(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("project_not_found".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_task_list_failed_{}", response.status().as_u16()));
        }

        response
            .json::<Vec<ProjectTaskRecord>>()
            .await
            .map_err(|_| "project_task_list_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Lists immutable project/task audit events through the owner-authenticated bridge.
#[tauri::command]
async fn list_project_activity(
    project_id: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<Vec<ProjectActivityRecord>, String> {
    if !valid_workspace_id(&project_id) {
        return Err("project_id_invalid".to_string());
    }
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let url = format!(
            "{}/{project_id}/activity",
            gateway_url(GATEWAY_PROJECTS_PATH)
        );
        let response = client
            .get(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("project_not_found".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_activity_list_failed_{}", response.status().as_u16()));
        }

        response
            .json::<Vec<ProjectActivityRecord>>()
            .await
            .map_err(|_| "project_activity_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Creates a task in a project via a fixed typed gateway route.
#[tauri::command]
async fn create_project_task(
    project_id: String,
    title: String,
    description: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectTaskRecord, String> {
    if !valid_workspace_id(&project_id) {
        return Err("project_id_invalid".to_string());
    }
    if title.trim().is_empty() || title.trim().len() > 160 || description.len() > 2000 {
        return Err("project_task_details_invalid".to_string());
    }
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let url = format!("{}/{project_id}/tasks", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client
            .post(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectTaskCreatePayload {
                title: &title,
                description: &description,
            })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("project_not_found".to_string());
        }
        if response.status() == reqwest::StatusCode::UNPROCESSABLE_ENTITY {
            return Err("project_task_details_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_task_create_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectTaskRecord>()
            .await
            .map_err(|_| "project_task_create_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Changes a task's status through the owner-authenticated native bridge.
#[tauri::command]
async fn update_project_task_status(
    task_id: String,
    status: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectTaskRecord, String> {
    if !valid_workspace_id(&task_id) {
        return Err("project_task_id_invalid".to_string());
    }
    if !["open", "in_progress", "done"].contains(&status.as_str()) {
        return Err("project_task_status_invalid".to_string());
    }
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let url = format!("{}/{task_id}/status", gateway_url(GATEWAY_TASKS_PATH));
        let response = client
            .patch(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectTaskStatusPayload { status: &status })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("project_task_not_found".to_string());
        }
        if response.status() == reqwest::StatusCode::UNPROCESSABLE_ENTITY {
            return Err("project_task_status_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_task_status_update_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectTaskRecord>()
            .await
            .map_err(|_| "project_task_status_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Updates a project's status through a typed native request. Only known status
/// values are accepted by the gateway, which appends an audit event per change.
#[tauri::command]
async fn update_project_status(
    project_id: String,
    status: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectRecord, String> {
    if !["active", "paused", "completed"].contains(&status.as_str()) {
        return Err("project_status_invalid".to_string());
    }
    if project_id.len() != 32 || !project_id.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err("project_id_invalid".to_string());
    }

    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let url = format!(
            "{}/status",
            gateway_url(&format!("{GATEWAY_PROJECTS_PATH}/{project_id}"))
        );
        let response = client
            .patch(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectStatusPayload { status: &status })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("project_not_found".to_string());
        }
        if response.status() == reqwest::StatusCode::UNPROCESSABLE_ENTITY {
            return Err("project_status_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_status_update_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectRecord>()
            .await
            .map_err(|_| "project_status_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Starts the native JARVIS desktop shell and its private gateway sidecar.
///
/// The process token is generated in native code and passed only to the gateway
/// environment. The owner token remains in native managed state and is only
/// attached by the fixed, typed API commands above.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_gateway_capabilities,
            get_owner_auth_status,
            setup_owner,
            login_owner,
            logout_owner,
            list_projects,
            create_project,
            update_project_status,
            list_project_tasks,
            create_project_task,
            update_project_task_status,
            list_project_activity
        ])
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
                owner_session: Mutex::new(None),
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building JARVIS desktop application");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(runtime) = handle.try_state::<GatewayRuntime>() {
                if let Ok(mut owner_session) = runtime.owner_session.lock() {
                    if let Some(token) = owner_session.as_mut() {
                        token.zeroize();
                    }
                    owner_session.take();
                }
                if let Ok(mut child_guard) = runtime.child.lock() {
                    if let Some(child) = child_guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}

impl Drop for GatewayRuntime {
    fn drop(&mut self) {
        self.session_token.zeroize();
        if let Ok(owner_session) = self.owner_session.get_mut() {
            if let Some(token) = owner_session.as_mut() {
                token.zeroize();
            }
        }
    }
}
