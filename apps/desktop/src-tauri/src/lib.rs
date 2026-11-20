use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

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

struct ApprovalNonce {
    value: String,
    expires_at: Instant,
}

fn prune_expired_approval_nonces(vault: &mut HashMap<String, ApprovalNonce>) {
    let now = Instant::now();
    vault.retain(|_, entry| {
        if entry.expires_at <= now {
            entry.value.zeroize();
            false
        } else {
            true
        }
    });
}

struct GatewayRuntime {
    child: Mutex<Option<CommandChild>>,
    session_token: String,
    owner_session: Mutex<Option<String>>,
    cloud_session: Mutex<Option<CloudSession>>,
    approval_nonces: Mutex<HashMap<String, ApprovalNonce>>,
}

#[derive(Clone)]
struct CloudSession {
    api_url: String,
    supabase_url: String,
    public_key: String,
    access_token: String,
    refresh_token: String,
    expires_at: u64,
    workspace_id: String,
    workspace_name: String,
    device_id: String,
    synced_projects: usize,
}

impl Drop for CloudSession {
    fn drop(&mut self) {
        self.public_key.zeroize();
        self.access_token.zeroize();
        self.refresh_token.zeroize();
    }
}

#[derive(Serialize, Deserialize)]
struct AiProviderConfig {
    api_key: String,
    model: String,
    endpoint: String,
}

impl Drop for AiProviderConfig {
    fn drop(&mut self) {
        self.api_key.zeroize();
    }
}

#[derive(Serialize)]
struct AiProviderStatus {
    configured: bool,
    model: String,
    endpoint: String,
}

#[cfg(target_os = "windows")]
fn ai_provider_entry() -> Result<keyring::Entry, String> {
    keyring::Entry::new("com.ceoglobal.jarvis", "ai-provider-config")
        .map_err(|_| "secure_credential_store_unavailable".to_string())
}

#[cfg(target_os = "windows")]
fn read_ai_provider_config() -> Option<AiProviderConfig> {
    let entry = ai_provider_entry().ok()?;
    let raw = entry.get_password().ok()?;
    serde_json::from_str(&raw).ok()
}

#[cfg(not(target_os = "windows"))]
fn read_ai_provider_config() -> Option<AiProviderConfig> {
    None
}

#[derive(Serialize)]
struct CloudSyncStatus {
    connected: bool,
    workspace_id: String,
    workspace_name: String,
    device_id: String,
    synced_projects: usize,
}

#[derive(Serialize, Deserialize, Clone)]
struct ConversationMessage {
    role: String,
    content: String,
}

#[derive(Serialize)]
struct ConversationRequest<'a> {
    messages: &'a [ConversationMessage],
}

#[derive(Deserialize, Serialize)]
struct ConversationReply {
    role: String,
    content: String,
}

#[derive(Deserialize, Serialize)]
struct CloudMemoryRecord {
    id: String,
    workspace_id: String,
    category: String,
    content: String,
    source_ref: String,
    created_at: String,
}

#[derive(Serialize)]
struct CloudMemoryCreatePayload<'a> {
    workspace_id: &'a str,
    category: &'a str,
    content: &'a str,
    source_ref: &'a str,
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
struct ApprovalRecord {
    id: String,
    project_id: String,
    action: String,
    arguments: serde_json::Value,
    arguments_hash: String,
    requester: String,
    status: String,
    created_at: f64,
    expires_at: f64,
    decided_at: Option<f64>,
    consumed_at: Option<f64>,
}
#[derive(Deserialize)]
struct ApprovalCreatedRecord {
    id: String,
    project_id: String,
    action: String,
    arguments: serde_json::Value,
    arguments_hash: String,
    requester: String,
    status: String,
    created_at: f64,
    expires_at: f64,
    nonce: String,
}
#[derive(Serialize)]
struct ApprovalCreatePayload {
    project_id: String,
    action: String,
    arguments: serde_json::Value,
    ttl_seconds: u16,
}
#[derive(Serialize)]
struct ApprovalDecisionPayload {
    approve: bool,
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

#[derive(Deserialize, Serialize)]
struct ProjectDecisionRecord {
    id: String,
    project_id: String,
    title: String,
    decision: String,
    rationale: String,
    source_ref: String,
    decided_at: f64,
    created_at: f64,
}

#[derive(Deserialize, Serialize)]
struct ProjectMilestoneRecord {
    id: String,
    project_id: String,
    title: String,
    description: String,
    target_at: Option<f64>,
    status: String,
    completed_at: Option<f64>,
    created_at: f64,
    updated_at: f64,
}


#[derive(Deserialize, Serialize)]
struct ProjectRiskRecord {
    id: String, project_id: String, title: String, description: String,
    severity: String, mitigation: String, status: String, created_at: f64, updated_at: f64,
}
#[derive(Deserialize, Serialize)]
struct ProjectMemoryRecord {
    id: String, project_id: String, category: String, content: String,
    source_ref: String, confidence: Option<f64>, created_at: f64,
}
#[derive(Serialize)]
struct ProjectRiskCreatePayload<'a> {
    title: &'a str, description: &'a str, severity: &'a str, mitigation: &'a str,
}
#[derive(Serialize)]
struct ProjectMemoryCreatePayload<'a> {
    category: &'a str, content: &'a str, source_ref: &'a str, confidence: Option<f64>,
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

#[derive(Serialize)]
struct ProjectDecisionCreatePayload<'a> {
    title: &'a str,
    decision: &'a str,
    rationale: &'a str,
    source_ref: &'a str,
}

#[derive(Serialize)]
struct ProjectMilestoneCreatePayload<'a> {
    title: &'a str,
    description: &'a str,
    target_at: Option<f64>,
}

#[derive(Serialize)]
struct ProjectMilestoneStatusPayload<'a> {
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
    if let Ok(mut vault) = runtime.approval_nonces.lock() {
        for entry in vault.values_mut() { entry.value.zeroize(); }
        vault.clear();
    }
    let cloud_session = runtime.cloud_session.lock().ok().and_then(|mut guard| guard.take());
    if let Some(cloud_session) = cloud_session {
        revoke_supabase_session(&cloud_session).await;
        drop(cloud_session);
    }
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


#[derive(Serialize)]
struct ApprovedExecutionPayload {
    approval_id: String,
    nonce: String,
    action: String,
    arguments: serde_json::Value,
}

#[tauri::command]
async fn execute_approved_project_task(
    approval_id: String,
    project_id: String,
    title: String,
    description: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<serde_json::Value, String> {
    if approval_id.trim().is_empty() || approval_id.len() > 64
        || !valid_workspace_id(&project_id)
        || title.trim().is_empty() || title.trim().len() > 160
        || description.len() > 2000 {
        return Err("approved_task_details_invalid".into());
    }

    let mut nonce = {
        let mut vault = runtime.approval_nonces.lock()
            .map_err(|_| "native_approval_vault_unavailable".to_string())?;
        prune_expired_approval_nonces(&mut vault);
        vault.remove(&approval_id)
            .ok_or_else(|| "approval_nonce_unavailable_or_expired".to_string())?
    };

    let mut owner_token = runtime.owner_session.lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone().ok_or_else(|| "owner_session_required".to_string())?;

    let arguments = serde_json::json!({
        "project_id": project_id,
        "title": title,
        "description": description
    });

    let result = async {
        let client = gateway_client()?;
        let response = client.post(gateway_url("/v1/execution/approved"))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", owner_token.as_str())
            .json(&ApprovedExecutionPayload {
                approval_id,
                nonce: nonce.value.clone(),
                action: "project.task.create".to_string(),
                arguments,
            })
            .send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".into());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("approval_or_project_not_found".into());
        }
        if response.status() == reqwest::StatusCode::CONFLICT {
            return Err("approval_invalid_expired_or_already_used".into());
        }
        if !response.status().is_success() {
            return Err(format!("approved_execution_failed_{}", response.status().as_u16()));
        }
        response.json::<serde_json::Value>().await
            .map_err(|_| "approved_execution_response_invalid".to_string())
    }.await;

    nonce.value.zeroize();
    owner_token.zeroize();
    result
}

/// Reads configured external provider status through a fixed native gateway route.
#[tauri::command]
async fn get_monitoring_overview(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<serde_json::Value, String> {
    let client = gateway_client()?;
    let mut owner_token = runtime.owner_session.lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone().ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let response = client.get(gateway_url("/v1/monitoring/providers/overview"))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("monitoring_overview_failed_{}", response.status().as_u16()));
        }
        response.json::<serde_json::Value>().await
            .map_err(|_| "monitoring_overview_response_invalid".to_string())
    }.await;
    owner_token.zeroize();
    result
}

/// Lists projects through the authenticated native bridge. The owner token is
/// required and is attached in Rust; it is never sent to the webview.

#[tauri::command]
async fn list_project_risks(project_id: String, runtime: tauri::State<'_, GatewayRuntime>) -> Result<Vec<ProjectRiskRecord>, String> {
    if !valid_workspace_id(&project_id) { return Err("project_id_invalid".into()); }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{project_id}/risks", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client.get(url).header("X-Jarvis-Session", &runtime.session_token).header("X-Jarvis-Owner-Session", &token).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if !response.status().is_success() { return Err(format!("project_risk_list_failed_{}", response.status().as_u16())); }
        response.json::<Vec<ProjectRiskRecord>>().await.map_err(|_| "project_risk_list_response_invalid".into())
    }.await;
    token.zeroize(); result
}

#[tauri::command]
async fn create_project_risk(project_id: String, title: String, description: String, severity: String, mitigation: String, runtime: tauri::State<'_, GatewayRuntime>) -> Result<ProjectRiskRecord, String> {
    if !valid_workspace_id(&project_id) { return Err("project_id_invalid".into()); }
    if title.trim().is_empty() || title.len() > 160 || description.len() > 2000 || mitigation.len() > 2000 || !["low","medium","high","critical"].contains(&severity.as_str()) { return Err("project_risk_details_invalid".into()); }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{project_id}/risks", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client.post(url).header("X-Jarvis-Session", &runtime.session_token).header("X-Jarvis-Owner-Session", &token).json(&ProjectRiskCreatePayload { title: &title, description: &description, severity: &severity, mitigation: &mitigation }).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if response.status() == reqwest::StatusCode::NOT_FOUND { return Err("project_not_found".into()); }
        if !response.status().is_success() { return Err(format!("project_risk_create_failed_{}", response.status().as_u16())); }
        response.json::<ProjectRiskRecord>().await.map_err(|_| "project_risk_create_response_invalid".into())
    }.await;
    token.zeroize(); result
}

#[tauri::command]
async fn update_project_risk_status(risk_id: String, status: String, runtime: tauri::State<'_, GatewayRuntime>) -> Result<ProjectRiskRecord, String> {
    if !valid_workspace_id(&risk_id) || !["open","mitigated","accepted","closed"].contains(&status.as_str()) { return Err("project_risk_status_invalid".into()); }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{risk_id}/status", gateway_url("/v1/risks"));
        let response = client.patch(url).header("X-Jarvis-Session", &runtime.session_token).header("X-Jarvis-Owner-Session", &token).json(&ProjectMilestoneStatusPayload { status: &status }).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if response.status() == reqwest::StatusCode::NOT_FOUND { return Err("project_risk_not_found".into()); }
        if !response.status().is_success() { return Err(format!("project_risk_status_failed_{}", response.status().as_u16())); }
        response.json::<ProjectRiskRecord>().await.map_err(|_| "project_risk_status_response_invalid".into())
    }.await;
    token.zeroize(); result
}

#[tauri::command]
async fn list_project_memory(project_id: String, runtime: tauri::State<'_, GatewayRuntime>) -> Result<Vec<ProjectMemoryRecord>, String> {
    if !valid_workspace_id(&project_id) { return Err("project_id_invalid".into()); }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{project_id}/memory", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client.get(url).header("X-Jarvis-Session", &runtime.session_token).header("X-Jarvis-Owner-Session", &token).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if !response.status().is_success() { return Err(format!("project_memory_list_failed_{}", response.status().as_u16())); }
        response.json::<Vec<ProjectMemoryRecord>>().await.map_err(|_| "project_memory_list_response_invalid".into())
    }.await;
    token.zeroize(); result
}

#[tauri::command]
async fn create_project_memory(project_id: String, category: String, content: String, source_ref: String, confidence: Option<f64>, runtime: tauri::State<'_, GatewayRuntime>) -> Result<ProjectMemoryRecord, String> {
    if !valid_workspace_id(&project_id) || content.trim().is_empty() || content.len() > 4000 || source_ref.len() > 1000 || !["fact","preference","decision","note","reference"].contains(&category.as_str()) || confidence.is_some_and(|v| !v.is_finite() || !(0.0..=1.0).contains(&v)) { return Err("project_memory_details_invalid".into()); }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{project_id}/memory", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client.post(url).header("X-Jarvis-Session", &runtime.session_token).header("X-Jarvis-Owner-Session", &token).json(&ProjectMemoryCreatePayload { category: &category, content: &content, source_ref: &source_ref, confidence }).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if response.status() == reqwest::StatusCode::NOT_FOUND { return Err("project_not_found".into()); }
        if !response.status().is_success() { return Err(format!("project_memory_create_failed_{}", response.status().as_u16())); }
        response.json::<ProjectMemoryRecord>().await.map_err(|_| "project_memory_create_response_invalid".into())
    }.await;
    token.zeroize(); result
}


#[tauri::command]
async fn list_project_approvals(project_id: String, runtime: tauri::State<'_, GatewayRuntime>) -> Result<Vec<ApprovalRecord>, String> {
    if !valid_workspace_id(&project_id) { return Err("project_id_invalid".into()); }
    {
        let mut vault = runtime.approval_nonces.lock().map_err(|_| "native_approval_vault_unavailable".to_string())?;
        prune_expired_approval_nonces(&mut vault);
    }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{}", gateway_url("/v1/approvals"), project_id);
        let response = client.get(url).header("X-Jarvis-Session", &runtime.session_token).header("X-Jarvis-Owner-Session", &token).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if !response.status().is_success() { return Err(format!("approval_list_failed_{}", response.status().as_u16())); }
        response.json::<Vec<ApprovalRecord>>().await.map_err(|_| "approval_list_response_invalid".into())
    }.await;
    token.zeroize(); result
}

#[tauri::command]
async fn create_project_approval(project_id: String, action: String, arguments: serde_json::Value, ttl_seconds: u16, runtime: tauri::State<'_, GatewayRuntime>) -> Result<ApprovalRecord, String> {
    if !valid_workspace_id(&project_id) || action.trim().is_empty() || action.len() > 120 || !(1..=900).contains(&ttl_seconds) || !arguments.is_object() {
        return Err("approval_request_details_invalid".into());
    }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let response = client.post(gateway_url("/v1/approvals"))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &token)
            .json(&ApprovalCreatePayload { project_id, action, arguments, ttl_seconds })
            .send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if !response.status().is_success() { return Err(format!("approval_create_failed_{}", response.status().as_u16())); }
        let created = response.json::<ApprovalCreatedRecord>().await.map_err(|_| "approval_create_response_invalid".to_string())?;
        {
            let mut vault = runtime.approval_nonces.lock().map_err(|_| "native_approval_vault_unavailable".to_string())?;
            prune_expired_approval_nonces(&mut vault);
            vault.insert(created.id.clone(), ApprovalNonce {
                value: created.nonce,
                expires_at: Instant::now() + Duration::from_secs(u64::from(ttl_seconds)),
            });
        }
        Ok(ApprovalRecord {
            id: created.id, project_id: created.project_id, action: created.action,
            arguments: created.arguments, arguments_hash: created.arguments_hash,
            requester: created.requester, status: created.status, created_at: created.created_at,
            expires_at: created.expires_at, decided_at: None, consumed_at: None,
        })
    }.await;
    token.zeroize(); result
}

#[tauri::command]
async fn decide_project_approval(approval_id: String, approve: bool, runtime: tauri::State<'_, GatewayRuntime>) -> Result<serde_json::Value, String> {
    if approval_id.trim().is_empty() || approval_id.len() > 64 { return Err("approval_id_invalid".into()); }
    let client = gateway_client()?;
    let mut token = runtime.owner_session.lock().map_err(|_| "native_owner_session_unavailable".to_string())?.clone().ok_or_else(|| "owner_session_required".to_string())?;
    let result = async {
        let url = format!("{}/{}/decision", gateway_url("/v1/approvals"), approval_id);
        let response = client.post(url).header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &token)
            .json(&ApprovalDecisionPayload { approve }).send().await.map_err(|_| "gateway_not_ready".to_string())?;
        if response.status() == reqwest::StatusCode::UNAUTHORIZED { return Err("owner_session_expired".into()); }
        if !response.status().is_success() { return Err(format!("approval_decision_failed_{}", response.status().as_u16())); }
        let value = response.json::<serde_json::Value>().await.map_err(|_| "approval_decision_response_invalid".to_string())?;
        if !approve {
            if let Ok(mut vault) = runtime.approval_nonces.lock() {
                prune_expired_approval_nonces(&mut vault);
                if let Some(mut entry) = vault.remove(&approval_id) { entry.value.zeroize(); }
            }
        }
        Ok(value)
    }.await;
    token.zeroize(); result
}


fn validate_cloud_https_url(raw: &str, label: &str) -> Result<String, String> {
    let value = raw.trim().trim_end_matches('/').to_string();
    let parsed = reqwest::Url::parse(&value).map_err(|_| format!("{label}_url_invalid"))?;
    if parsed.scheme() != "https"
        || parsed.host_str().is_none()
        || !parsed.username().is_empty()
        || parsed.password().is_some()
    {
        return Err(format!("{label}_must_use_https"));
    }
    Ok(value)
}

fn cloud_now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn cloud_http_client() -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .timeout(Duration::from_secs(20))
        .build()
        .map_err(|_| "cloud_http_client_unavailable".to_string())
}

async fn cloud_sync_project_records(
    client: &reqwest::Client,
    session: &mut CloudSession,
    projects: &[ProjectRecord],
) -> Result<usize, String> {
    if session.expires_at <= cloud_now_epoch() + 60 {
        let response = client
            .post(format!(
                "{}/auth/v1/token?grant_type=refresh_token",
                session.supabase_url
            ))
            .header("apikey", &session.public_key)
            .json(&serde_json::json!({ "refresh_token": session.refresh_token }))
            .send()
            .await
            .map_err(|_| "cloud_auth_refresh_unavailable".to_string())?;
        if !response.status().is_success() {
            return Err("cloud_session_expired_reconnect_required".to_string());
        }
        let data = response
            .json::<serde_json::Value>()
            .await
            .map_err(|_| "cloud_auth_refresh_response_invalid".to_string())?;
        let access = data["access_token"]
            .as_str()
            .ok_or_else(|| "cloud_auth_refresh_response_invalid".to_string())?
            .to_string();
        let refresh = data["refresh_token"]
            .as_str()
            .unwrap_or(&session.refresh_token)
            .to_string();
        let expires_in = data["expires_in"].as_u64().unwrap_or(3600);
        session.access_token.zeroize();
        session.refresh_token.zeroize();
        session.access_token = access;
        session.refresh_token = refresh;
        session.expires_at = cloud_now_epoch() + expires_in;
    }

    let mut synced = 0usize;
    for project in projects {
        let response = client
            .post(format!("{}/v1/projects/sync", session.api_url))
            .bearer_auth(&session.access_token)
            .json(&serde_json::json!({
                "workspace_id": session.workspace_id,
                "source_local_id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "priority": "normal"
            }))
            .send()
            .await
            .map_err(|_| "cloud_project_sync_unavailable".to_string())?;
        if !response.status().is_success() {
            return Err(format!("cloud_project_sync_failed_{}", response.status().as_u16()));
        }
        synced += 1;
    }
    session.synced_projects = synced;
    Ok(synced)
}

#[tauri::command]
async fn connect_cloud_and_sync(
    api_url: String,
    supabase_url: String,
    public_key: String,
    email: String,
    password: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<CloudSyncStatus, String> {
    let password = zeroize::Zeroizing::new(password);
    let api_url = validate_cloud_https_url(&api_url, "cloud_api")?;
    let supabase_url = validate_cloud_https_url(&supabase_url, "supabase")?;
    let public_key = public_key.trim().to_string();
    if public_key.is_empty() || public_key.len() > 512 {
        return Err("supabase_public_key_required".to_string());
    }
    if email.trim().is_empty() || password.is_empty() {
        return Err("cloud_email_and_password_required".to_string());
    }

    let owner_token = zeroize::Zeroizing::new(
        runtime
            .owner_session
            .lock()
            .map_err(|_| "native_owner_session_unavailable".to_string())?
            .clone()
            .ok_or_else(|| "owner_session_required".to_string())?,
    );

    let local_client = gateway_client()?;
    let local_projects_result = async {
        let response = local_client
            .get(gateway_url(GATEWAY_PROJECTS_PATH))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", owner_token.as_str())
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;
        if !response.status().is_success() {
            return Err(format!("local_project_list_failed_{}", response.status().as_u16()));
        }
        response
            .json::<Vec<ProjectRecord>>()
            .await
            .map_err(|_| "local_project_list_response_invalid".to_string())
    }
    .await;
    let local_projects = local_projects_result?;

    let client = cloud_http_client()?;
    let auth_result = client
        .post(format!("{}/auth/v1/token?grant_type=password", supabase_url))
        .header("apikey", &public_key)
        .json(&serde_json::json!({ "email": email.trim(), "password": password.as_str() }))
        .send()
        .await;
    let auth_response = auth_result.map_err(|_| "supabase_auth_unavailable".to_string())?;
    if !auth_response.status().is_success() {
        return Err(format!("supabase_sign_in_failed_{}", auth_response.status().as_u16()));
    }
    let auth_data = auth_response
        .json::<serde_json::Value>()
        .await
        .map_err(|_| "supabase_auth_response_invalid".to_string())?;
    let access_token = auth_data["access_token"]
        .as_str()
        .ok_or_else(|| "supabase_session_not_returned_confirm_email_or_sign_in".to_string())?
        .to_string();
    let refresh_token = auth_data["refresh_token"]
        .as_str()
        .ok_or_else(|| "supabase_refresh_token_missing".to_string())?
        .to_string();
    let expires_in = auth_data["expires_in"].as_u64().unwrap_or(3600);

    let mut session = CloudSession {
        api_url,
        supabase_url,
        public_key,
        access_token,
        refresh_token,
        expires_at: cloud_now_epoch() + expires_in,
        workspace_id: String::new(),
        workspace_name: String::new(),
        device_id: String::new(),
        synced_projects: 0,
    };

    let workspaces_response = client
        .get(format!("{}/v1/workspaces", session.api_url))
        .bearer_auth(&session.access_token)
        .send()
        .await
        .map_err(|_| "cloud_workspace_list_unavailable".to_string())?;
    if !workspaces_response.status().is_success() {
        return Err(format!("cloud_workspace_list_failed_{}", workspaces_response.status().as_u16()));
    }
    let mut workspaces = workspaces_response
        .json::<Vec<serde_json::Value>>()
        .await
        .map_err(|_| "cloud_workspace_list_invalid".to_string())?;
    if workspaces.is_empty() {
        let created = client
            .post(format!("{}/v1/workspaces", session.api_url))
            .bearer_auth(&session.access_token)
            .json(&serde_json::json!({ "name": "JARVIS Workspace", "timezone": "Africa/Lagos", "locale": "en-NG" }))
            .send()
            .await
            .map_err(|_| "cloud_workspace_create_unavailable".to_string())?;
        if !created.status().is_success() {
            return Err(format!("cloud_workspace_create_failed_{}", created.status().as_u16()));
        }
        workspaces.push(created.json::<serde_json::Value>().await
            .map_err(|_| "cloud_workspace_create_response_invalid".to_string())?);
    }
    let workspace = workspaces.first().ok_or_else(|| "cloud_workspace_missing".to_string())?;
    session.workspace_id = workspace["id"].as_str()
        .ok_or_else(|| "cloud_workspace_id_missing".to_string())?.to_string();
    session.workspace_name = workspace["name"].as_str().unwrap_or("JARVIS Workspace").to_string();

    let devices_response = client
        .get(format!("{}/v1/devices", session.api_url))
        .query(&[("workspace_id", session.workspace_id.as_str())])
        .bearer_auth(&session.access_token)
        .send()
        .await
        .map_err(|_| "cloud_device_list_unavailable".to_string())?;
    if !devices_response.status().is_success() {
        return Err(format!("cloud_device_list_failed_{}", devices_response.status().as_u16()));
    }
    let devices = devices_response
        .json::<Vec<serde_json::Value>>()
        .await
        .map_err(|_| "cloud_device_list_invalid".to_string())?;
    if let Some(existing) = devices.iter().find(|device| {
        device["platform"] == "windows" && device["device_name"] == "JARVIS Windows Desktop"
    }) {
        session.device_id = existing["id"].as_str().unwrap_or_default().to_string();
        let _ = client
            .post(format!("{}/v1/devices/{}/heartbeat", session.api_url, session.device_id))
            .bearer_auth(&session.access_token)
            .send()
            .await;
    } else {
        let registered = client
            .post(format!("{}/v1/devices", session.api_url))
            .bearer_auth(&session.access_token)
            .json(&serde_json::json!({
                "workspace_id": session.workspace_id,
                "device_name": "JARVIS Windows Desktop",
                "platform": "windows",
                "app_version": env!("CARGO_PKG_VERSION")
            }))
            .send()
            .await
            .map_err(|_| "cloud_device_register_unavailable".to_string())?;
        if !registered.status().is_success() {
            return Err(format!("cloud_device_register_failed_{}", registered.status().as_u16()));
        }
        let data = registered.json::<serde_json::Value>().await
            .map_err(|_| "cloud_device_register_response_invalid".to_string())?;
        session.device_id = data["id"].as_str().unwrap_or_default().to_string();
    }

    let synced = cloud_sync_project_records(&client, &mut session, &local_projects).await?;
    let status = CloudSyncStatus {
        connected: true,
        workspace_id: session.workspace_id.clone(),
        workspace_name: session.workspace_name.clone(),
        device_id: session.device_id.clone(),
        synced_projects: synced,
    };
    let mut guard = runtime.cloud_session.lock()
        .map_err(|_| "native_cloud_session_unavailable".to_string())?;
    *guard = Some(session);
    Ok(status)
}

#[tauri::command]
async fn sync_cloud_projects(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<CloudSyncStatus, String> {
    let mut session = runtime.cloud_session.lock()
        .map_err(|_| "native_cloud_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "cloud_account_not_connected".to_string())?;
    let mut owner_token = runtime.owner_session.lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;
    let local_client = gateway_client()?;
    let local_result = async {
        let response = local_client
            .get(gateway_url(GATEWAY_PROJECTS_PATH))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", owner_token.as_str())
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;
        if !response.status().is_success() {
            return Err(format!("local_project_list_failed_{}", response.status().as_u16()));
        }
        response.json::<Vec<ProjectRecord>>().await
            .map_err(|_| "local_project_list_response_invalid".to_string())
    }.await;
    let projects = local_result?;
    let client = cloud_http_client()?;
    let synced = cloud_sync_project_records(&client, &mut session, &projects).await?;
    let status = CloudSyncStatus {
        connected: true,
        workspace_id: session.workspace_id.clone(),
        workspace_name: session.workspace_name.clone(),
        device_id: session.device_id.clone(),
        synced_projects: synced,
    };
    let mut guard = runtime.cloud_session.lock()
        .map_err(|_| "native_cloud_session_unavailable".to_string())?;
    *guard = Some(session);
    Ok(status)
}

async fn revoke_supabase_session(session: &CloudSession) {
    if let Ok(client) = cloud_http_client() {
        let _ = client
            .post(format!("{}/auth/v1/logout", session.supabase_url))
            .header("apikey", &session.public_key)
            .bearer_auth(&session.access_token)
            .send()
            .await;
    }
}

#[tauri::command]
async fn disconnect_cloud(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<(), String> {
    let session = {
        let mut guard = runtime.cloud_session.lock()
            .map_err(|_| "native_cloud_session_unavailable".to_string())?;
        guard.take()
    };
    if let Some(session) = session {
        revoke_supabase_session(&session).await;
        drop(session);
    }
    Ok(())
}

#[tauri::command]
fn get_cloud_sync_status(
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<Option<CloudSyncStatus>, String> {
    let guard = runtime.cloud_session.lock()
        .map_err(|_| "native_cloud_session_unavailable".to_string())?;
    Ok(guard.as_ref().map(|session| CloudSyncStatus {
        connected: true,
        workspace_id: session.workspace_id.clone(),
        workspace_name: session.workspace_name.clone(),
        device_id: session.device_id.clone(),
        synced_projects: session.synced_projects,
    }))
}

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

/// Lists milestones for one validated owner project.
#[tauri::command]
async fn list_project_milestones(
    project_id: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<Vec<ProjectMilestoneRecord>, String> {
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
        let url = format!("{}/{project_id}/milestones", gateway_url(GATEWAY_PROJECTS_PATH));
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
            return Err(format!("project_milestone_list_failed_{}", response.status().as_u16()));
        }

        response
            .json::<Vec<ProjectMilestoneRecord>>()
            .await
            .map_err(|_| "project_milestone_list_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Creates a milestone with an optional target timestamp.
#[tauri::command]
async fn create_project_milestone(
    project_id: String,
    title: String,
    description: String,
    target_at: Option<f64>,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectMilestoneRecord, String> {
    if !valid_workspace_id(&project_id) {
        return Err("project_id_invalid".to_string());
    }
    if title.trim().is_empty() || title.trim().len() > 160 || description.len() > 2000 {
        return Err("project_milestone_details_invalid".to_string());
    }
    if let Some(target) = target_at {
        if !target.is_finite() || target < 0.0 {
            return Err("project_milestone_target_invalid".to_string());
        }
    }
    let client = gateway_client()?;
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let url = format!("{}/{project_id}/milestones", gateway_url(GATEWAY_PROJECTS_PATH));
        let response = client
            .post(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectMilestoneCreatePayload {
                title: &title,
                description: &description,
                target_at,
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
            return Err("project_milestone_details_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_milestone_create_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectMilestoneRecord>()
            .await
            .map_err(|_| "project_milestone_create_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Updates a milestone's status via the owner-authenticated bridge.
#[tauri::command]
async fn update_project_milestone_status(
    milestone_id: String,
    status: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectMilestoneRecord, String> {
    if !valid_workspace_id(&milestone_id) {
        return Err("project_milestone_id_invalid".to_string());
    }
    if !["planned", "in_progress", "completed", "cancelled"].contains(&status.as_str()) {
        return Err("project_milestone_status_invalid".to_string());
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
            "{}/{milestone_id}/status",
            gateway_url("/v1/milestones")
        );
        let response = client
            .patch(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectMilestoneStatusPayload { status: &status })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::NOT_FOUND {
            return Err("project_milestone_not_found".to_string());
        }
        if response.status() == reqwest::StatusCode::UNPROCESSABLE_ENTITY {
            return Err("project_milestone_status_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_milestone_status_update_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectMilestoneRecord>()
            .await
            .map_err(|_| "project_milestone_status_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Lists the append-only decision journal for one validated owner project.
#[tauri::command]
async fn list_project_decisions(
    project_id: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<Vec<ProjectDecisionRecord>, String> {
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
            "{}/{project_id}/decisions",
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
            return Err(format!("project_decision_list_failed_{}", response.status().as_u16()));
        }

        response
            .json::<Vec<ProjectDecisionRecord>>()
            .await
            .map_err(|_| "project_decision_list_response_invalid".to_string())
    }
    .await;

    owner_token.zeroize();
    result
}

/// Records a project decision through the native owner-authenticated bridge.
#[tauri::command]
async fn create_project_decision(
    project_id: String,
    title: String,
    decision: String,
    rationale: String,
    source_ref: String,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ProjectDecisionRecord, String> {
    if !valid_workspace_id(&project_id) {
        return Err("project_id_invalid".to_string());
    }
    if title.trim().is_empty() || decision.trim().is_empty() {
        return Err("project_decision_details_invalid".to_string());
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
            "{}/{project_id}/decisions",
            gateway_url(GATEWAY_PROJECTS_PATH)
        );
        let response = client
            .post(url)
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ProjectDecisionCreatePayload {
                title: &title,
                decision: &decision,
                rationale: &rationale,
                source_ref: &source_ref,
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
            return Err("project_decision_details_invalid".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("project_decision_create_failed_{}", response.status().as_u16()));
        }

        response
            .json::<ProjectDecisionRecord>()
            .await
            .map_err(|_| "project_decision_create_response_invalid".to_string())
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

/// Store the AI provider credential in Windows Credential Manager.
#[tauri::command]
fn save_ai_provider_config(
    mut api_key: String,
    model: String,
    endpoint: Option<String>,
) -> Result<AiProviderStatus, String> {
    let model = model.trim().to_string();
    let endpoint = endpoint.unwrap_or_else(|| "https://api.openai.com/v1/chat/completions".to_string());
    let endpoint = endpoint.trim().to_string();
    if api_key.trim().len() < 10 || api_key.len() > 4096 || model.is_empty() || model.len() > 120 {
        api_key.zeroize();
        return Err("ai_provider_configuration_invalid".to_string());
    }
    if !endpoint.starts_with("https://") || endpoint.len() > 500 {
        api_key.zeroize();
        return Err("ai_provider_endpoint_must_use_https".to_string());
    }
    #[cfg(target_os = "windows")]
    {
        let config = AiProviderConfig { api_key: api_key.clone(), model: model.clone(), endpoint: endpoint.clone() };
        let serialized = serde_json::to_string(&config)
            .map_err(|_| "ai_provider_configuration_invalid".to_string())?;
        let entry = ai_provider_entry()?;
        entry.set_password(&serialized)
            .map_err(|_| "secure_credential_store_write_failed".to_string())?;
        api_key.zeroize();
        return Ok(AiProviderStatus { configured: true, model, endpoint });
    }
    #[cfg(not(target_os = "windows"))]
    {
        api_key.zeroize();
        Err("secure_ai_provider_storage_supported_on_windows_only".to_string())
    }
}

#[tauri::command]
fn get_ai_provider_status() -> AiProviderStatus {
    match read_ai_provider_config() {
        Some(config) => AiProviderStatus {
            configured: true,
            model: config.model,
            endpoint: config.endpoint,
        },
        None => AiProviderStatus {
            configured: false,
            model: String::new(),
            endpoint: "https://api.openai.com/v1/chat/completions".to_string(),
        },
    }
}

/// Sends a bounded conversation through the authenticated local gateway.
/// The owner session and process token never leave the native Rust process.
#[tauri::command]
async fn send_conversation(
    messages: Vec<ConversationMessage>,
    runtime: tauri::State<'_, GatewayRuntime>,
) -> Result<ConversationReply, String> {
    if messages.is_empty() || messages.len() > 20 {
        return Err("conversation_messages_invalid".to_string());
    }
    let mut owner_token = runtime
        .owner_session
        .lock()
        .map_err(|_| "native_owner_session_unavailable".to_string())?
        .clone()
        .ok_or_else(|| "owner_session_required".to_string())?;

    let result = async {
        let client = gateway_client()?;
        let response = client
            .post(gateway_url("/v1/conversation/reply"))
            .header("X-Jarvis-Session", &runtime.session_token)
            .header("X-Jarvis-Owner-Session", &owner_token)
            .json(&ConversationRequest { messages: &messages })
            .send()
            .await
            .map_err(|_| "gateway_not_ready".to_string())?;

        if response.status() == reqwest::StatusCode::UNAUTHORIZED {
            return Err("owner_session_expired".to_string());
        }
        if response.status() == reqwest::StatusCode::SERVICE_UNAVAILABLE {
            return Err("conversation_provider_not_configured".to_string());
        }
        if response.status() == reqwest::StatusCode::BAD_GATEWAY {
            return Err("conversation_provider_unavailable".to_string());
        }
        if !response.status().is_success() {
            return Err(format!("conversation_request_failed_{}", response.status().as_u16()));
        }
        response.json::<ConversationReply>().await
            .map_err(|_| "conversation_response_invalid".to_string())
    }.await;

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
            connect_cloud_and_sync,
            sync_cloud_projects,
            get_cloud_sync_status,
            send_conversation,
            save_ai_provider_config,
            get_ai_provider_status,
            list_cloud_memory,
            create_cloud_memory,
            disconnect_cloud,
            setup_owner,
            login_owner,
            logout_owner,
            list_projects,
            create_project,
            update_project_status,
            list_project_tasks,
            create_project_task,
            update_project_task_status,
            list_project_activity,
            list_project_decisions,
            create_project_decision,
            list_project_milestones,
            create_project_milestone,
            update_project_milestone_status,
            list_project_risks,
            create_project_risk,
            update_project_risk_status,
            list_project_memory,
            create_project_memory,
            get_monitoring_overview,
            list_project_approvals,
            create_project_approval,
            decide_project_approval,
            execute_approved_project_task
        ])
        .setup(|app| {
            let token = new_session_token();
            let provider = read_ai_provider_config();
            let mut sidecar = app.shell().sidecar("jarvis-gateway")
                .map_err(|error| format!("gateway_sidecar_unavailable: {error}"))?
                .args(["--host", "127.0.0.1", "--port", "8765"])
                .env("JARVIS_SESSION_TOKEN", token.clone());
            if let Some(config) = provider.as_ref() {
                sidecar = sidecar
                    .env("JARVIS_AI_API_KEY", config.api_key.clone())
                    .env("JARVIS_AI_MODEL", config.model.clone())
                    .env("JARVIS_AI_ENDPOINT", config.endpoint.clone());
            }
            let child = match sidecar
                Ok(command) => match command
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
                cloud_session: Mutex::new(None),
                approval_nonces: Mutex::new(HashMap::new()),
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
                if let Ok(mut cloud_session) = runtime.cloud_session.lock() {
                    drop(cloud_session.take());
                }
                if let Ok(mut vault) = runtime.approval_nonces.lock() {
                    for entry in vault.values_mut() {
                        entry.value.zeroize();
                    }
                    vault.clear();
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
        if let Ok(vault) = self.approval_nonces.get_mut() {
            for entry in vault.values_mut() { entry.value.zeroize(); }
            vault.clear();
        }
    }
}
