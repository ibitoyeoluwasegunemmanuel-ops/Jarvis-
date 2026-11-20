import { FormEvent, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import {
  Activity,
  AudioLines,
  BrainCircuit,
  ChevronRight,
  Command,
  FolderKanban,
  LayoutDashboard,
  Mic,
  MonitorUp,
  Radio,
  ShieldCheck,
  Settings,
  Sparkles,
  TerminalSquare
} from "lucide-react";

type Health = { status: string; service?: string; version?: string };
type MonitoringProvider = {
  provider: string; status: "connected" | "not_configured" | "unavailable";
  detail?: string; deployments?: Array<{ id: string; name: string; url: string; state: string; created_at?: number; target: string }>;
  projects?: Array<{ ref: string; name: string; region: string; status: string; created_at: string }>;
};
type MonitoringOverview = { read_only: boolean; providers: MonitoringProvider[] };
type GatewayCapabilities = {
  capabilities: {
    gateway_session_authentication: boolean;
    agent_execution: boolean;
    persistent_memory: boolean;
    voice: boolean;
    computer_use: boolean;
  };
  security: {
    gateway_session_configured: boolean;
    owner_authentication_configured: boolean;
    owner_session_authenticated: boolean;
  };
};
type OwnerAuthStatus = {
  owner_configured: boolean;
  setup_required: boolean;
  authenticated: boolean;
};
type CloudMemoryRecord = {
  id: string; workspace_id: string; category: "preference" | "fact" | "decision" | "note" | "reference";
  content: string; source_ref: string; created_at: string;
};
type AiProviderStatus = { configured: boolean; model: string; endpoint: string };
type CloudSyncStatus = {
  connected: boolean;
  workspace_id: string;
  workspace_name: string;
  device_id: string;
  synced_projects: number;
};

type Project = {
  id: string;
  name: string;
  description: string;
  status: "active" | "paused" | "completed";
  created_at: number;
  updated_at: number;
};

type ProjectTask = {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: "open" | "in_progress" | "done";
  created_at: number;
  updated_at: number;
};

type ProjectActivity = {
  id: number;
  event_type: string;
  entity_type: string;
  entity_id: string;
  details_json: string;
  occurred_at: number;
};

type ProjectDecision = {
  id: string;
  project_id: string;
  title: string;
  decision: string;
  rationale: string;
  source_ref: string;
  decided_at: number;
  created_at: number;
};

type ProjectRisk = {
  id: string; project_id: string; title: string; description: string;
  severity: "low" | "medium" | "high" | "critical"; mitigation: string;
  status: "open" | "mitigated" | "accepted" | "closed"; created_at: number; updated_at: number;
};
type ProjectMemory = {
  id: string; project_id: string; category: "fact" | "preference" | "decision" | "note" | "reference";
  content: string; source_ref: string; confidence: number | null; created_at: number;
};

type ProjectApproval = {
  id: string; project_id: string; action: string; arguments: Record<string, unknown>;
  arguments_hash: string; requester: string;
  status: "pending" | "approved" | "denied" | "consumed" | "expired";
  created_at: number; expires_at: number; decided_at: number | null; consumed_at: number | null;
};

type ProjectMilestone = {
  id: string;
  project_id: string;
  title: string;
  description: string;
  target_at: number | null;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  completed_at: number | null;
  created_at: number;
  updated_at: number;
};

const gateway = import.meta.env.VITE_GATEWAY_URL ?? "http://127.0.0.1:8765";

function readableAuthError(error: unknown): string {
  const message = String(error);
  if (message.includes("invalid_owner_credentials")) return "That password is not correct.";
  if (message.includes("owner_login_temporarily_locked")) {
    return "Too many attempts. Wait one minute before trying again.";
  }
  if (message.includes("owner_already_configured")) {
    return "The owner account already exists. Sign in instead.";
  }
  if (message.includes("password_does_not_meet_security_requirements")) {
    return "Use a password with at least 12 characters.";
  }
  if (message.includes("owner_setup_or_account_state_conflict")) {
    return "The account state changed. Refresh JARVIS and try again.";
  }
  if (message.includes("gateway_not_ready")) return "The secure local service is still starting.";
  return "JARVIS could not complete that secure sign-in request.";
}

function AuthScreen({
  setupRequired,
  busy,
  error,
  nativeUnavailable,
  onSubmit
}: {
  setupRequired: boolean;
  busy: boolean;
  error: string;
  nativeUnavailable: boolean;
  onSubmit: (password: string, confirmation: string) => Promise<void>;
}) {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [localError, setLocalError] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError("");
    if (setupRequired && password !== confirmation) {
      setLocalError("The passwords do not match.");
      return;
    }
    if (password.length < 12) {
      setLocalError("Use at least 12 characters.");
      return;
    }
    const submittedPassword = password;
    const submittedConfirmation = confirmation;
    setPassword("");
    setConfirmation("");
    await onSubmit(submittedPassword, submittedConfirmation);
  };

  return (
    <main className="auth-shell">
      <section className="auth-card">
        <div className="auth-logo"><Sparkles size={22}/></div>
        <div className="auth-brand">JARVIS <span>PRIVATE AI WORKSPACE</span></div>
        <div className="auth-eyebrow">{setupRequired ? "FIRST-RUN SECURITY SETUP" : "OWNER SIGN-IN"}</div>
        <h1>{setupRequired ? "Secure your workspace." : "Welcome back."}</h1>
        <p className="auth-description">
          {setupRequired
            ? "Create the private owner password for this Windows installation. Your password is stored as a secure hash on this device."
            : "Sign in to unlock your private JARVIS workspace. Your session stays inside the native application."}
        </p>
        {nativeUnavailable ? (
          <div className="auth-alert">
            Open the installed JARVIS Windows app to continue. Secure sign-in is not available in browser preview.
          </div>
        ) : (
          <form className="auth-form" onSubmit={submit}>
            <label htmlFor="owner-password">{setupRequired ? "Create password" : "Owner password"}</label>
            <input
              id="owner-password"
              type="password"
              autoComplete={setupRequired ? "new-password" : "current-password"}
              minLength={12}
              maxLength={256}
              required
              value={password}
              onChange={event => setPassword(event.target.value)}
              placeholder="At least 12 characters"
            />
            {setupRequired && (
              <>
                <label htmlFor="owner-password-confirm">Confirm password</label>
                <input
                  id="owner-password-confirm"
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  maxLength={256}
                  required
                  value={confirmation}
                  onChange={event => setConfirmation(event.target.value)}
                  placeholder="Enter the same password again"
                />
              </>
            )}
            {(localError || error) && <div className="auth-error">{localError || error}</div>}
            <button type="submit" disabled={busy}>
              {busy ? "Securing workspace…" : setupRequired ? "Create owner account" : "Unlock JARVIS"}
            </button>
          </form>
        )}
        <div className="auth-footnote">
          <ShieldCheck size={14}/>
          Password verification happens in the local gateway. The browser interface never receives your session token.
        </div>
      </section>
    </main>
  );
}

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};
type WorkspacePanel = "home" | "github" | "projects" | "calendar";

function LiveWorkspace({ onOpenProjects }: { onOpenProjects: () => void }) {
  const [panel, setPanel] = useState<WorkspacePanel>("home");
  const [command, setCommand] = useState("");
  const [response, setResponse] = useState("I am ready. Choose a workspace panel or ask me a question.");
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [thinking, setThinking] = useState(false);
  const [conversationError, setConversationError] = useState("");
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const startVoiceInput = () => {
    const SpeechRecognitionCtor = (window as SpeechWindow).SpeechRecognition
      || (window as SpeechWindow).webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) {
      setVoiceError("Speech recognition is not available in this Windows WebView. You can still type to JARVIS.");
      return;
    }
    try {
      const recognition = new SpeechRecognitionCtor();
      recognition.lang = "en-NG";
      recognition.interimResults = false;
      recognition.continuous = false;
      recognition.onresult = event => {
        const transcript = event.results[0]?.[0]?.transcript?.trim();
        if (transcript) setCommand(transcript);
      };
      recognition.onerror = () => {
        setVoiceError("Microphone input could not be started. Check Windows microphone permission.");
        setListening(false);
      };
      recognition.onend = () => setListening(false);
      recognitionRef.current = recognition;
      setVoiceError("");
      setListening(true);
      recognition.start();
    } catch {
      setListening(false);
      setVoiceError("Microphone input could not be started. Check Windows microphone permission.");
    }
  };
  const speakLatest = () => {
    if (!("speechSynthesis" in window)) {
      setVoiceError("Speech output is not available in this Windows WebView.");
      return;
    }
    window.speechSynthesis.cancel();
    const latest = [...messages].reverse().find(message => message.role === "assistant")?.content || response;
    const utterance = new SpeechSynthesisUtterance(latest);
    utterance.lang = "en-NG";
    utterance.rate = 1;
    utterance.pitch = 0.96;
    window.speechSynthesis.speak(utterance);
    setVoiceError("");
  };
  const openPanel = (next: WorkspacePanel) => {
    setPanel(next);
    const messages: Record<WorkspacePanel, string> = {
      home: "Your JARVIS workspace is ready.",
      github: "GitHub workspace selected. The repository link below opens your connected JARVIS source. Live account authorisation and repository data sync are not connected yet.",
      projects: "Your locally stored JARVIS projects are available in the Projects section. Cloud-wide project and task synchronisation is still being expanded.",
      calendar: "Calendar panel selected. Connect a calendar integration to load events; no calendar account is connected yet."
    };
    setResponse(messages[next]);
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const value = command.trim();
    if (!value) return;
    const normalized = value.toLowerCase().replace(/[.!?]/g, " ");
    const requestedPanel: WorkspacePanel | null =
      /\b(github|git hub|repository|repo)\b/.test(normalized) ? "github" :
      /\b(projects?|tasks?)\b/.test(normalized) ? "projects" :
      /\b(calendar|schedule|events?)\b/.test(normalized) ? "calendar" :
      /\b(home|overview|dashboard)\b/.test(normalized) ? "home" : null;
    if (requestedPanel) {
      openPanel(requestedPanel);
      if (requestedPanel === "projects") onOpenProjects();
      setResponse(
        requestedPanel === "github"
          ? "Opening your JARVIS GitHub workspace. Use the repository link in the panel to open GitHub."
          : requestedPanel === "projects"
            ? "Opening your Projects section."
            : requestedPanel === "calendar"
              ? "Showing the calendar panel. No calendar account is connected yet."
              : "Showing your JARVIS overview."
      );
    } else {
      const nextMessages = [...messages, { role: "user" as const, content: value }].slice(-20);
      setMessages(nextMessages);
      setConversationError("");
      setThinking(true);
      setResponse("Thinking…");
      setCommand("");
      try {
        const reply = await invoke<{ role: "assistant"; content: string }>("send_conversation", { messages: nextMessages });
        setMessages([...nextMessages, reply].slice(-20));
        setResponse(reply.content);
      } catch (error) {
        const message = String(error);
        const friendly = message.includes("conversation_provider_not_configured")
          ? "The conversation engine is connected, but an AI provider key and model have not been configured on this computer yet."
          : message.includes("owner_session_expired")
            ? "Your secure JARVIS session expired. Sign in again to continue."
            : message.includes("conversation_provider_unavailable")
              ? "The AI provider could not be reached. Check the provider connection and try again."
              : "JARVIS could not complete the conversation request.";
        setConversationError(friendly);
        setResponse(friendly);
      } finally {
        setThinking(false);
      }
      return;
    }
    setCommand("");
  };
  return <section className="live-workspace" aria-label="JARVIS live workspace">
    <div className="live-workspace-head"><div><span className="eyebrow">LIVE WORKSPACE</span><h3>Talk to JARVIS. Work in one place.</h3></div><span className="workspace-state"><span/> WORKSPACE READY</span></div>
    <div className="workspace-layout">
      <aside className="workspace-avatar"><div className="avatar-orbit"><div className="avatar-core"><Sparkles size={30}/></div></div><b>JARVIS</b><small>PERSONAL AI ASSISTANT</small><div className="presence-status"><span/> Ready for your command</div><p>{response}</p><div className="voice-controls">
        <button type="button" onClick={listening ? () => recognitionRef.current?.stop() : startVoiceInput} disabled={thinking}>
          <Mic size={14}/> {listening ? "Stop listening" : "Speak to JARVIS"}
        </button>
        <button type="button" onClick={speakLatest} disabled={thinking}> <AudioLines size={14}/> Speak reply </button>
      </div>
      {voiceError && <small className="workspace-notice">{voiceError}</small>}</aside>
      <div className="workspace-main"><nav className="workspace-tabs" aria-label="Workspace panels">
        <button className={panel === "home" ? "selected" : ""} onClick={() => openPanel("home")}>Overview</button>
        <button className={panel === "github" ? "selected" : ""} onClick={() => openPanel("github")}>GitHub</button>
        <button className={panel === "projects" ? "selected" : ""} onClick={() => openPanel("projects")}>Projects</button>
        <button className={panel === "calendar" ? "selected" : ""} onClick={() => openPanel("calendar")}>Calendar</button>
      </nav>
      <div className="workspace-panel">
        {panel === "home" && <><div className="workspace-panel-icon"><BrainCircuit size={22}/></div><h4>Your command workspace</h4><p>Open connected tools and keep the assistant conversation beside your work. JARVIS will show connection status honestly and ask before taking consequential actions.</p><div className="workspace-shortcuts"><button onClick={() => openPanel("github")}><Command size={16}/> Open GitHub panel <ChevronRight size={15}/></button><button onClick={() => openPanel("projects")}><FolderKanban size={16}/> View projects <ChevronRight size={15}/></button></div></>}
        {panel === "github" && <><div className="workspace-panel-icon"><TerminalSquare size={22}/></div><span className="eyebrow">GITHUB WORKSPACE</span><h4>JARVIS source repository</h4><p>Open the active development branch and review commits, pull requests and build checks.</p><a className="workspace-external-link" href="https://github.com/ibitoyeoluwasegunemmanuel-ops/Jarvis-/tree/feature/cross-device-foundation" target="_blank" rel="noreferrer">Open JARVIS on GitHub <ChevronRight size={15}/></a><small className="workspace-notice">GitHub account authorisation and live repository data are not yet integrated inside JARVIS.</small></>}
        {panel === "projects" && <><div className="workspace-panel-icon"><FolderKanban size={22}/></div><h4>Project management</h4><p>Use the existing Projects section to manage locally stored projects, tasks, decisions, risks and approvals.</p><button className="workspace-action" onClick={onOpenProjects}>Go to Projects <ChevronRight size={15}/></button></>}
        {panel === "calendar" && <><div className="workspace-panel-icon"><Activity size={22}/></div><h4>Calendar connection</h4><p>No calendar provider is connected yet. Calendar authorisation will be added as a scoped integration.</p><span className="workspace-notice">NOT CONNECTED</span></>}
      </div></div>
      {messages.length > 0 && <div className="conversation-thread" aria-live="polite">
        {messages.map((message, index) => <div className={"conversation-message " + message.role} key={index}>
          <span>{message.role === "user" ? "YOU" : "JARVIS"}</span><p>{message.content}</p>
        </div>)}
        {thinking && <div className="conversation-thinking"><span/> JARVIS is thinking…</div>}
        {conversationError && <div className="workspace-notice">{conversationError}</div>}
      </div>}
    </div>
    <form className="workspace-command" onSubmit={submit}><Sparkles size={17}/><input value={command} onChange={event => setCommand(event.target.value)} placeholder="Tell JARVIS what you want to open or do…" aria-label="JARVIS command"/><button type="button" className="voice-input-button" onClick={listening ? () => recognitionRef.current?.stop() : startVoiceInput} aria-label={listening ? "Stop microphone" : "Start microphone"} disabled={thinking}><Mic size={15}/></button><button type="submit" disabled={!command.trim() || thinking}>Send <ChevronRight size={15}/></button></form>
  </section>;
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [monitoring, setMonitoring] = useState<MonitoringOverview | null>(null);
  const [monitoringLoading, setMonitoringLoading] = useState(false);
  const [monitoringRefreshKey, setMonitoringRefreshKey] = useState(0);
  const [monitoringError, setMonitoringError] = useState("");
  const [capabilities, setCapabilities] = useState<GatewayCapabilities | null>(null);
  const [capabilitiesError, setCapabilitiesError] = useState(false);
  const [authStatus, setAuthStatus] = useState<OwnerAuthStatus | null>(null);
  const [nativeUnavailable, setNativeUnavailable] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [active, setActive] = useState("Overview");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectError, setProjectError] = useState("");
  const [aiProviderStatus, setAiProviderStatus] = useState<AiProviderStatus | null>(null);
  const [aiProviderKey, setAiProviderKey] = useState("");
  const [aiProviderModel, setAiProviderModel] = useState("");
  const [aiProviderEndpoint, setAiProviderEndpoint] = useState("https://api.openai.com/v1/chat/completions");
  const [aiProviderBusy, setAiProviderBusy] = useState(false);
  const [aiProviderMessage, setAiProviderMessage] = useState("");
  const [cloudApiUrl, setCloudApiUrl] = useState("");
  const [cloudSupabaseUrl, setCloudSupabaseUrl] = useState("");
  const [cloudPublicKey, setCloudPublicKey] = useState("");
  const [cloudEmail, setCloudEmail] = useState("");
  const [cloudPassword, setCloudPassword] = useState("");
  const [cloudSyncStatus, setCloudSyncStatus] = useState<CloudSyncStatus | null>(null);
  const [cloudSyncBusy, setCloudSyncBusy] = useState(false);
  const [cloudSyncError, setCloudSyncError] = useState("");
  const [cloudMemories, setCloudMemories] = useState<CloudMemoryRecord[]>([]);
  const [cloudMemoryCategory, setCloudMemoryCategory] = useState<CloudMemoryRecord["category"]>("fact");
  const [cloudMemoryContent, setCloudMemoryContent] = useState("");
  const [cloudMemorySource, setCloudMemorySource] = useState("");
  const [cloudMemoryBusy, setCloudMemoryBusy] = useState(false);
  const [cloudMemoryError, setCloudMemoryError] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  const [updatingProjectId, setUpdatingProjectId] = useState<string | null>(null);
  const [activeTaskProjectId, setActiveTaskProjectId] = useState<string | null>(null);
  const [tasksByProject, setTasksByProject] = useState<Record<string, ProjectTask[]>>({});
  const [activityByProject, setActivityByProject] = useState<Record<string, ProjectActivity[]>>({});
  const [decisionsByProject, setDecisionsByProject] = useState<Record<string, ProjectDecision[]>>({});
  const [milestonesByProject, setMilestonesByProject] = useState<Record<string, ProjectMilestone[]>>({});
  const [risksByProject, setRisksByProject] = useState<Record<string, ProjectRisk[]>>({});
  const [memoryByProject, setMemoryByProject] = useState<Record<string, ProjectMemory[]>>({});
  const [approvalsByProject, setApprovalsByProject] = useState<Record<string, ProjectApproval[]>>({});
  const [approvalAction, setApprovalAction] = useState("project.task.create");
  const [approvalArguments, setApprovalArguments] = useState('{\n  "url": "https://example.com"\n}');
  const [approvalBusyId, setApprovalBusyId] = useState<string | null>(null);
  const [riskTitle, setRiskTitle] = useState("");
  const [riskDescription, setRiskDescription] = useState("");
  const [riskSeverity, setRiskSeverity] = useState<ProjectRisk["severity"]>("medium");
  const [riskMitigation, setRiskMitigation] = useState("");
  const [memoryCategory, setMemoryCategory] = useState<ProjectMemory["category"]>("fact");
  const [memoryContent, setMemoryContent] = useState("");
  const [memorySourceRef, setMemorySourceRef] = useState("");
  const [milestoneTitle, setMilestoneTitle] = useState("");
  const [milestoneDescription, setMilestoneDescription] = useState("");
  const [milestoneTargetDate, setMilestoneTargetDate] = useState("");
  const [savingMilestoneProjectId, setSavingMilestoneProjectId] = useState<string | null>(null);
  const [updatingMilestoneId, setUpdatingMilestoneId] = useState<string | null>(null);
  const [decisionTitle, setDecisionTitle] = useState("");
  const [decisionText, setDecisionText] = useState("");
  const [decisionRationale, setDecisionRationale] = useState("");
  const [decisionSourceRef, setDecisionSourceRef] = useState("");
  const [savingDecisionProjectId, setSavingDecisionProjectId] = useState<string | null>(null);
  const [tasksLoadingProjectId, setTasksLoadingProjectId] = useState<string | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [creatingTaskProjectId, setCreatingTaskProjectId] = useState<string | null>(null);
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);
  const [taskError, setTaskError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let retryTimer: number | undefined;
    let nativeStatusLoaded = false;
    let lastNativeStatusCheck = 0;

    const checkGateway = async () => {
      try {
        const response = await fetch(`${gateway}/health`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error("Gateway unavailable");
        setHealth(await response.json() as Health);
        setHealthError(false);

        if (!nativeStatusLoaded || Date.now() - lastNativeStatusCheck >= 60_000) {
          try {
            const result = await invoke<GatewayCapabilities>("get_gateway_capabilities");
            const owner = await invoke<OwnerAuthStatus>("get_owner_auth_status");
            if (!controller.signal.aborted) {
              setCapabilities(result);
              setCapabilitiesError(false);
              setAuthStatus(owner);
              setNativeUnavailable(false);
              nativeStatusLoaded = true;
              lastNativeStatusCheck = Date.now();
            }
          } catch {
            if (!controller.signal.aborted) {
              setCapabilitiesError(true);
              setNativeUnavailable(true);
              nativeStatusLoaded = false;
            }
          }
        }
      } catch {
        if (!controller.signal.aborted) {
          setHealth(null);
          setHealthError(true);
        }
      } finally {
        if (!controller.signal.aborted) {
          retryTimer = window.setTimeout(checkGateway, 3000);
        }
      }
    };

    void checkGateway();
    return () => {
      controller.abort();
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
    };
  }, []);

  useEffect(() => {
    if (!authStatus?.authenticated) return;
    let cancelled = false;
    invoke<CloudSyncStatus | null>("get_cloud_sync_status")
      .then(status => { if (!cancelled) setCloudSyncStatus(status); })
      .catch(() => { if (!cancelled) setCloudSyncStatus(null); });
    return () => { cancelled = true; };
  }, [authStatus?.authenticated]);

  const connectCloudAndSync = async (event: FormEvent) => {
    event.preventDefault();
    const submittedPassword = cloudPassword;
    setCloudPassword("");
    setCloudSyncBusy(true);
    setCloudSyncError("");
    try {
      const status = await invoke<CloudSyncStatus>("connect_cloud_and_sync", {
        apiUrl: cloudApiUrl,
        supabaseUrl: cloudSupabaseUrl,
        publicKey: cloudPublicKey,
        email: cloudEmail,
        password: submittedPassword
      });
      setCloudSyncStatus(status);
    } catch (error) {
      setCloudSyncError(String(error));
    } finally {
      setCloudSyncBusy(false);
    }
  };

  const disconnectCloud = async () => {
    setCloudSyncBusy(true);
    setCloudSyncError("");
    try {
      await invoke("disconnect_cloud");
      setCloudSyncStatus(null);
    } catch (error) {
      setCloudSyncError(String(error));
    } finally {
      setCloudSyncBusy(false);
    }
  };

  const syncCloudProjects = async () => {
    setCloudSyncBusy(true);
    setCloudSyncError("");
    try {
      const status = await invoke<CloudSyncStatus>("sync_cloud_projects");
      setCloudSyncStatus(status);
    } catch (error) {
      setCloudSyncError(String(error));
    } finally {
      setCloudSyncBusy(false);
    }
  };

  const refreshCloudMemory = async () => {
    setCloudMemoryBusy(true);
    setCloudMemoryError("");
    try {
      const entries = await invoke<CloudMemoryRecord[]>("list_cloud_memory");
      setCloudMemories(entries);
    } catch (error) {
      setCloudMemoryError(String(error).includes("cloud_account_not_connected")
        ? "Connect the shared cloud workspace in Projects first."
        : "JARVIS could not load shared memory. Check the cloud API connection.");
    } finally {
      setCloudMemoryBusy(false);
    }
  };

  const submitCloudMemory = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!cloudMemoryContent.trim() || cloudMemoryBusy) return;
    setCloudMemoryBusy(true);
    setCloudMemoryError("");
    try {
      const entry = await invoke<CloudMemoryRecord>("create_cloud_memory", {
        category: cloudMemoryCategory,
        content: cloudMemoryContent.trim(),
        sourceRef: cloudMemorySource.trim()
      });
      setCloudMemories(current => [entry, ...current]);
      setCloudMemoryContent("");
      setCloudMemorySource("");
    } catch (error) {
      setCloudMemoryError(String(error).includes("cloud_account_not_connected")
        ? "Connect the shared cloud workspace in Projects first."
        : "JARVIS could not save this shared memory entry.");
    } finally {
      setCloudMemoryBusy(false);
    }
  };

  useEffect(() => {
    if (active !== "Settings") return;
    invoke<AiProviderStatus>("get_ai_provider_status")
      .then(status => {
        setAiProviderStatus(status);
        setAiProviderModel(status.model || "");
        setAiProviderEndpoint(status.endpoint);
      })
      .catch(() => setAiProviderMessage("Secure provider settings are unavailable on this device."));
  }, [active]);

  useEffect(() => {
    if (active !== "Memory" || !cloudSyncStatus?.connected) return;
    let cancelled = false;
    setCloudMemoryBusy(true);
    setCloudMemoryError("");
    invoke<CloudMemoryRecord[]>("list_cloud_memory")
      .then(entries => {
        if (!cancelled) setCloudMemories(entries);
      })
      .catch(error => {
        if (cancelled) return;
        setCloudMemoryError(String(error).includes("cloud_account_not_connected")
          ? "Connect the shared cloud workspace in Projects first."
          : "JARVIS could not load shared memory. Check the cloud API connection.");
      })
      .finally(() => {
        if (!cancelled) setCloudMemoryBusy(false);
      });
    return () => { cancelled = true; };
  }, [active, cloudSyncStatus?.connected]);

  const submitOwnerAuth = async (password: string, _confirmation: string) => {
    setAuthBusy(true);
    setAuthError("");
    try {
      const command = authStatus?.setup_required ? "setup_owner" : "login_owner";
      await invoke(command, { password });
      const [owner, result] = await Promise.all([
        invoke<OwnerAuthStatus>("get_owner_auth_status"),
        invoke<GatewayCapabilities>("get_gateway_capabilities")
      ]);
      setAuthStatus(owner);
      setCapabilities(result);
      if (!owner.authenticated) setAuthError("The owner session could not be verified.");
    } catch (error) {
      setAuthError(readableAuthError(error));
    } finally {
      setAuthBusy(false);
    }
  };

  const logout = async () => {
    setAuthBusy(true);
    setAuthError("");
    try {
      await invoke("logout_owner");
      const owner = await invoke<OwnerAuthStatus>("get_owner_auth_status");
      setAuthStatus(owner);
    } catch (error) {
      setAuthError(readableAuthError(error));
    } finally {
      setAuthBusy(false);
    }
  };

  useEffect(() => {
    if (!authStatus?.authenticated) return;

    let cancelled = false;
    setProjectsLoading(true);
    setProjectError("");

    invoke<Project[]>("list_projects")
      .then(items => {
        if (!cancelled) setProjects(items);
      })
      .catch(error => {
        if (cancelled) return;
        const message = String(error);
        if (message.includes("owner_session_expired") || message.includes("owner_session_required")) {
          setAuthStatus(current => current
            ? { ...current, authenticated: false }
            : current
          );
          setProjectError("Your owner session expired. Sign in again to view projects.");
        } else {
          setProjectError("JARVIS could not load the local project list.");
        }
      })
      .finally(() => {
        if (!cancelled) setProjectsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [authStatus?.authenticated]);

  const syncCloudQuietly = async () => {
    if (!cloudSyncStatus?.connected) return;
    try {
      const status = await invoke<CloudSyncStatus>("sync_cloud_projects");
      setCloudSyncStatus(status);
      setCloudSyncError("");
    } catch (error) {
      setCloudSyncError(`Saved locally, but cloud sync needs attention: ${String(error)}`);
    }
  };

  const changeProjectStatus = async (projectId: string, status: Project["status"]) => {
    setUpdatingProjectId(projectId);
    setProjectError("");
    try {
      const updated = await invoke<Project>("update_project_status", {
        projectId,
        status
      });
      setProjects(current => current.map(item => item.id === updated.id ? updated : item));
      await syncCloudQuietly();
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current
          ? { ...current, authenticated: false }
          : current
        );
        setProjectError("Your owner session expired. Sign in again to update this project.");
      } else {
        setProjectError("JARVIS could not update this project status.");
      }
    } finally {
      setUpdatingProjectId(null);
    }
  };

  const submitProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const name = projectName.trim();
    if (!name || creatingProject) return;

    setCreatingProject(true);
    setProjectError("");
    try {
      const project = await invoke<Project>("create_project", {
        name,
        description: projectDescription.trim()
      });
      setProjects(current => [project, ...current.filter(item => item.id !== project.id)]);
      await syncCloudQuietly();
      setProjectName("");
      setProjectDescription("");
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current
          ? { ...current, authenticated: false }
          : current
        );
        setProjectError("Your owner session expired. Sign in again to create a project.");
      } else if (detail.includes("project_details_invalid")) {
        setProjectError("Check the project name and description, then try again.");
      } else {
        setProjectError("JARVIS could not save this project. Your draft is still available.");
        setProjectName(name);
        setProjectDescription(projectDescription);
      }
    } finally {
      setCreatingProject(false);
    }
  };

  const toggleProjectTasks = async (projectId: string) => {
    if (activeTaskProjectId === projectId) {
      setActiveTaskProjectId(null);
      setTaskError("");
      return;
    }

    setActiveTaskProjectId(projectId);
    setTaskError("");
    if (
      tasksByProject[projectId]
      && activityByProject[projectId]
      && decisionsByProject[projectId]
      && milestonesByProject[projectId]
      && risksByProject[projectId]
      && memoryByProject[projectId]
      && approvalsByProject[projectId]
    ) return;

    setTasksLoadingProjectId(projectId);
    try {
      const [tasks, activity, decisions, milestones, risks, memory, approvals] = await Promise.all([
        invoke<ProjectTask[]>("list_project_tasks", { projectId }),
        invoke<ProjectActivity[]>("list_project_activity", { projectId }),
        invoke<ProjectDecision[]>("list_project_decisions", { projectId }),
        invoke<ProjectMilestone[]>("list_project_milestones", { projectId }),
        invoke<ProjectRisk[]>("list_project_risks", { projectId }),
        invoke<ProjectMemory[]>("list_project_memory", { projectId }),
        invoke<ProjectApproval[]>("list_project_approvals", { projectId })
      ]);
      setTasksByProject(current => ({ ...current, [projectId]: tasks }));
      setActivityByProject(current => ({ ...current, [projectId]: activity }));
      setDecisionsByProject(current => ({ ...current, [projectId]: decisions }));
      setMilestonesByProject(current => ({ ...current, [projectId]: milestones }));
      setRisksByProject(current => ({ ...current, [projectId]: risks }));
      setMemoryByProject(current => ({ ...current, [projectId]: memory }));
      setApprovalsByProject(current => ({ ...current, [projectId]: approvals }));
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
      }
      setTaskError("JARVIS could not load tasks and activity for this project.");
    } finally {
      setTasksLoadingProjectId(null);
    }
  };

  const refreshProjectActivity = async (projectId: string) => {
    const activity = await invoke<ProjectActivity[]>("list_project_activity", { projectId });
    setActivityByProject(current => ({ ...current, [projectId]: activity }));
  };

  const submitProjectTask = async (
    event: FormEvent<HTMLFormElement>,
    projectId: string
  ) => {
    event.preventDefault();
    const title = taskTitle.trim();
    if (!title || creatingTaskProjectId) return;

    setCreatingTaskProjectId(projectId);
    setTaskError("");
    try {
      const task = await invoke<ProjectTask>("create_project_task", {
        projectId,
        title,
        description: taskDescription.trim()
      });
      setTasksByProject(current => ({
        ...current,
        [projectId]: [task, ...(current[projectId] ?? []).filter(item => item.id !== task.id)]
      }));
      try {
        await refreshProjectActivity(projectId);
      } catch {
        setTaskError("Task saved, but the activity timeline could not refresh.");
      }
      setTaskTitle("");
      setTaskDescription("");
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
        setTaskError("Your owner session expired. Sign in again to add tasks.");
      } else {
        setTaskError("JARVIS could not save this task. Your draft is still available.");
      }
    } finally {
      setCreatingTaskProjectId(null);
    }
  };

  const submitProjectMilestone = async (
    event: FormEvent<HTMLFormElement>,
    projectId: string
  ) => {
    event.preventDefault();
    const title = milestoneTitle.trim();
    if (!title || savingMilestoneProjectId) return;

    setSavingMilestoneProjectId(projectId);
    setTaskError("");
    const targetAt = milestoneTargetDate
      ? new Date(`${milestoneTargetDate}T00:00:00`).getTime() / 1000
      : null;
    try {
      const milestone = await invoke<ProjectMilestone>("create_project_milestone", {
        projectId,
        title,
        description: milestoneDescription.trim(),
        targetAt
      });
      setMilestonesByProject(current => ({
        ...current,
        [projectId]: [...(current[projectId] ?? []), milestone]
          .sort((a, b) => (a.target_at ?? Number.MAX_SAFE_INTEGER) - (b.target_at ?? Number.MAX_SAFE_INTEGER))
      }));
      try {
        await refreshProjectActivity(projectId);
      } catch {
        setTaskError("Milestone saved, but the activity timeline could not refresh.");
      }
      setMilestoneTitle("");
      setMilestoneDescription("");
      setMilestoneTargetDate("");
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
        setTaskError("Your owner session expired. Sign in again to add milestones.");
      } else {
        setTaskError("JARVIS could not save this milestone. Your draft is still available.");
      }
    } finally {
      setSavingMilestoneProjectId(null);
    }
  };

  const changeProjectMilestoneStatus = async (
    projectId: string,
    milestoneId: string,
    status: ProjectMilestone["status"]
  ) => {
    setUpdatingMilestoneId(milestoneId);
    setTaskError("");
    try {
      const updated = await invoke<ProjectMilestone>("update_project_milestone_status", {
        milestoneId,
        status
      });
      setMilestonesByProject(current => ({
        ...current,
        [projectId]: (current[projectId] ?? []).map(item => item.id === milestoneId ? updated : item)
      }));
      try {
        await refreshProjectActivity(projectId);
      } catch {
        setTaskError("Milestone updated, but the activity timeline could not refresh.");
      }
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
        setTaskError("Your owner session expired. Sign in again to update milestones.");
      } else {
        setTaskError("JARVIS could not update this milestone.");
      }
    } finally {
      setUpdatingMilestoneId(null);
    }
  };

  const submitProjectDecision = async (
    event: FormEvent<HTMLFormElement>,
    projectId: string
  ) => {
    event.preventDefault();
    const title = decisionTitle.trim();
    const decision = decisionText.trim();
    if (!title || !decision || savingDecisionProjectId) return;

    setSavingDecisionProjectId(projectId);
    setTaskError("");
    try {
      const record = await invoke<ProjectDecision>("create_project_decision", {
        projectId,
        title,
        decision,
        rationale: decisionRationale.trim(),
        sourceRef: decisionSourceRef.trim()
      });
      setDecisionsByProject(current => ({
        ...current,
        [projectId]: [record, ...(current[projectId] ?? []).filter(item => item.id !== record.id)]
      }));
      try {
        await refreshProjectActivity(projectId);
      } catch {
        setTaskError("Decision saved, but the activity timeline could not refresh.");
      }
      setDecisionTitle("");
      setDecisionText("");
      setDecisionRationale("");
      setDecisionSourceRef("");
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
        setTaskError("Your owner session expired. Sign in again to record a decision.");
      } else {
        setTaskError("JARVIS could not record this decision. Your draft is still available.");
      }
    } finally {
      setSavingDecisionProjectId(null);
    }
  };

  const submitProjectRisk = async (event: FormEvent<HTMLFormElement>, projectId: string) => {
    event.preventDefault();
    if (!riskTitle.trim()) return;
    try {
      const item = await invoke<ProjectRisk>("create_project_risk", {
        projectId, title: riskTitle.trim(), description: riskDescription.trim(),
        severity: riskSeverity, mitigation: riskMitigation.trim()
      });
      setRisksByProject(current => ({ ...current, [projectId]: [item, ...(current[projectId] ?? [])] }));
      setRiskTitle(""); setRiskDescription(""); setRiskMitigation("");
      await refreshProjectActivity(projectId);
    } catch {
      setTaskError("JARVIS could not save this project risk.");
    }
  };

  const changeProjectRiskStatus = async (projectId: string, riskId: string, status: ProjectRisk["status"]) => {
    try {
      const updated = await invoke<ProjectRisk>("update_project_risk_status", { riskId, status });
      setRisksByProject(current => ({ ...current, [projectId]: (current[projectId] ?? []).map(item => item.id === riskId ? updated : item) }));
      await refreshProjectActivity(projectId);
    } catch {
      setTaskError("JARVIS could not update this risk.");
    }
  };

  const submitProjectMemory = async (event: FormEvent<HTMLFormElement>, projectId: string) => {
    event.preventDefault();
    if (!memoryContent.trim()) return;
    try {
      const item = await invoke<ProjectMemory>("create_project_memory", {
        projectId, category: memoryCategory, content: memoryContent.trim(),
        sourceRef: memorySourceRef.trim(), confidence: null
      });
      setMemoryByProject(current => ({ ...current, [projectId]: [item, ...(current[projectId] ?? [])] }));
      setMemoryContent(""); setMemorySourceRef("");
      await refreshProjectActivity(projectId);
    } catch {
      setTaskError("JARVIS could not save this memory entry.");
    }
  };

  const submitProjectApproval = async (event: FormEvent<HTMLFormElement>, projectId: string) => {
    event.preventDefault();
    let parsed: Record<string, unknown>;
    try {
      const value: unknown = JSON.parse(approvalArguments);
      if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Arguments must be a JSON object.");
      parsed = value as Record<string, unknown>;
      if (approvalAction.trim() === "project.task.create") {
        if (typeof parsed.title !== "string" || typeof parsed.description !== "string") {
          throw new Error("Task approvals require title and description strings.");
        }
        parsed.project_id = projectId;
      }
    } catch {
      setTaskError("Approval arguments must be a valid JSON object.");
      return;
    }
    setTaskError("");
    try {
      const created = await invoke<ProjectApproval>("create_project_approval", {
        projectId, action: approvalAction.trim(), arguments: parsed, ttlSeconds: 300
      });
      const latest = await invoke<ProjectApproval[]>("list_project_approvals", { projectId });
      setApprovalsByProject(current => ({ ...current, [projectId]: latest }));
      await refreshProjectActivity(projectId);
      setTaskError("");
      void created;
    } catch (error) {
      setTaskError(String(error).includes("owner_session") ? "Your owner session expired. Sign in again." : "JARVIS could not create this approval request.");
    }
  };

  const executeApprovedTask = async (projectId: string, approval: ProjectApproval) => {
    const args = approval.arguments;
    if (approval.action !== "project.task.create" || args.project_id !== projectId || typeof args.title !== "string" || typeof args.description !== "string") {
      setTaskError("This approval is not a valid project task creation request."); return;
    }
    setApprovalBusyId(approval.id); setTaskError("");
    try {
      await invoke("execute_approved_project_task", { approvalId: approval.id, projectId, title: args.title, description: args.description });
      const [tasks, approvals] = await Promise.all([invoke<ProjectTask[]>("list_project_tasks", { projectId }), invoke<ProjectApproval[]>("list_project_approvals", { projectId })]);
      setTasksByProject(current => ({ ...current, [projectId]: tasks }));
      setApprovalsByProject(current => ({ ...current, [projectId]: approvals }));
      await refreshProjectActivity(projectId);
    } catch (error) {
      const detail = String(error);
      setTaskError(detail.includes("approval_nonce") || detail.includes("approval_invalid") ? "The approval is no longer usable. Create a new approval request and approve it again." : "JARVIS could not execute this approved task.");
    } finally { setApprovalBusyId(null); }
  };
  const reviewProjectApproval = async (projectId: string, approvalId: string, approve: boolean) => {
    setApprovalBusyId(approvalId);
    setTaskError("");
    try {
      await invoke("decide_project_approval", { approvalId, approve });
      const latest = await invoke<ProjectApproval[]>("list_project_approvals", { projectId });
      setApprovalsByProject(current => ({ ...current, [projectId]: latest }));
      await refreshProjectActivity(projectId);
    } catch {
      setTaskError("JARVIS could not record that approval decision.");
    } finally {
      setApprovalBusyId(null);
    }
  };

  const changeProjectTaskStatus = async (
    projectId: string,
    taskId: string,
    status: ProjectTask["status"]
  ) => {
    setUpdatingTaskId(taskId);
    setTaskError("");
    try {
      const updated = await invoke<ProjectTask>("update_project_task_status", {
        taskId,
        status
      });
      setTasksByProject(current => ({
        ...current,
        [projectId]: (current[projectId] ?? []).map(item => item.id === taskId ? updated : item)
      }));
      try {
        await refreshProjectActivity(projectId);
      } catch {
        setTaskError("Task updated, but the activity timeline could not refresh.");
      }
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
        setTaskError("Your owner session expired. Sign in again to update tasks.");
      } else {
        setTaskError("JARVIS could not update this task.");
      }
    } finally {
      setUpdatingTaskId(null);
    }
  };

  useEffect(() => {
    if (active !== "Monitoring" || !authStatus?.authenticated) return;
    let cancelled = false;
    setMonitoringLoading(true);
    setMonitoringError("");
    invoke<MonitoringOverview>("get_monitoring_overview")
      .then(result => { if (!cancelled) setMonitoring(result); })
      .catch(error => {
        if (cancelled) return;
        if (String(error).includes("owner_session_expired")) {
          setAuthStatus(current => current ? { ...current, authenticated: false } : current);
        }
        setMonitoringError("JARVIS could not retrieve provider status. Check the local gateway and owner session.");
      })
      .finally(() => { if (!cancelled) setMonitoringLoading(false); });
    return () => { cancelled = true; };
  }, [active, authStatus?.authenticated, monitoringRefreshKey]);

  const nav = [
    { label: "Overview", icon: LayoutDashboard },
    { label: "Projects", icon: FolderKanban },
    { label: "AI Workspace", icon: BrainCircuit },
    { label: "Memory", icon: BrainCircuit },
    { label: "Engineering", icon: TerminalSquare },
    { label: "Security", icon: ShieldCheck },
    { label: "Analytics", icon: Activity },
    { label: "Monitoring", icon: Radio },
    { label: "Settings", icon: Settings }
  ];

  if (!authStatus || !authStatus.authenticated) {
    return (
      <AuthScreen
        setupRequired={authStatus?.setup_required ?? false}
        busy={authBusy}
        error={authError}
        nativeUnavailable={nativeUnavailable}
        onSubmit={submitOwnerAuth}
      />
    );
  }

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Sparkles size={19}/></div><div><strong>JARVIS</strong><span>PERSONAL AI SYSTEM</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{nav.map(item => <button key={item.label} className={active === item.label ? "nav-item active" : "nav-item"} onClick={() => setActive(item.label)}><item.icon size={17}/><span>{item.label}</span>{active === item.label && <ChevronRight size={15}/>}</button>)}</nav>
      <div className="sidebar-bottom">
        <div className="secure-pill"><ShieldCheck size={15}/> Private workspace</div>
        <div className="profile">
          <div className="avatar-mini">C</div>
          <div><b>Owner</b><span>Authenticated locally</span></div>
          <button className="logout-button" onClick={logout} disabled={authBusy}>Sign out</button>
        </div>
      </div>
    </aside>
    <section className="main-panel">
      <header className="topbar"><div className="breadcrumb">JARVIS <span>/</span> {active}</div><div className="top-actions"><span className={health?.status === "ok" ? "status online" : "status"}><i/> {health?.status === "ok" ? "Gateway connected" : healthError ? "Gateway offline" : "Connecting…"}</span><button className="icon-button" aria-label="Command menu"><Command size={17}/></button></div></header>
      <div className="content">
        {authError && <div className="dashboard-error">{authError}</div>}
        <div className="welcome-row"><div><div className="eyebrow"><span className="pulse"/> SYSTEM INITIALISING</div><h1>Your workspace.<br/><em>One intelligent system.</em></h1><p className="lead">A unified environment for building, analysing, researching and operating your projects.</p></div><div className="presence-card"><div className="presence-orb"><AudioLines size={27}/></div><div><b>JARVIS presence</b><span>Voice interface is being prepared</span></div><span className="coming">IN DEVELOPMENT</span></div></div>
        {active === "Settings" ? (
          <section className="projects-workspace">
            <div className="section-heading">
              <div><span className="eyebrow">PRIVATE CONFIGURATION</span><h2>AI provider settings</h2></div>
              <span className="tag">{aiProviderStatus?.configured ? "PROVIDER SAVED" : "NOT CONFIGURED"}</span>
            </div>
            <p className="monitor-intro">Your API key is saved in Windows Credential Manager. JARVIS never sends it to the webview or stores it in this repository.</p>
            <article className="panel-card">
              <div className="panel-title"><div><span className="eyebrow">CONVERSATION ENGINE</span><h3>Connect an AI provider</h3></div><ShieldCheck size={18}/></div>
              <form className="project-form" onSubmit={async event => {
                event.preventDefault();
                setAiProviderBusy(true);
                setAiProviderMessage("");
                try {
                  const status = await invoke<AiProviderStatus>("save_ai_provider_config", {
                    apiKey: aiProviderKey,
                    model: aiProviderModel,
                    endpoint: aiProviderEndpoint
                  });
                  setAiProviderStatus(status);
                  setAiProviderKey("");
                  setAiProviderMessage("Saved securely. Restart JARVIS to activate the provider connection.");
                } catch (error) {
                  setAiProviderMessage(String(error).includes("secure_ai_provider_storage_supported_on_windows_only")
                    ? "Secure provider storage is currently available on Windows only."
                    : "JARVIS could not save the provider settings securely.");
                } finally {
                  setAiProviderBusy(false);
                }
              }}>
                <label htmlFor="ai-provider-key">API key</label>
                <input id="ai-provider-key" type="password" autoComplete="off" required minLength={10} maxLength={4096} value={aiProviderKey} onChange={event => setAiProviderKey(event.target.value)} placeholder={aiProviderStatus?.configured ? "Enter a new key to replace the saved key" : "Paste your provider API key"}/>
                <label htmlFor="ai-provider-model">Model</label>
                <input id="ai-provider-model" required maxLength={120} value={aiProviderModel} onChange={event => setAiProviderModel(event.target.value)} placeholder="Provider model identifier"/>
                <label htmlFor="ai-provider-endpoint">HTTPS API endpoint</label>
                <input id="ai-provider-endpoint" required maxLength={500} type="url" value={aiProviderEndpoint} onChange={event => setAiProviderEndpoint(event.target.value)} placeholder="https://api.openai.com/v1/chat/completions"/>
                <button className="primary-button" type="submit" disabled={aiProviderBusy || !aiProviderKey.trim() || !aiProviderModel.trim()}>
                  {aiProviderBusy ? "Saving securely…" : "Save provider settings"}
                </button>
              </form>
              {aiProviderMessage && <div className="workspace-notice">{aiProviderMessage}</div>}
              {aiProviderStatus?.configured && (
                <div className="provider-saved-actions">
                  <p className="monitor-intro">Saved model: {aiProviderStatus.model}. The secret is not displayed again.</p>
                  <button type="button" className="secondary-button" disabled={aiProviderBusy} onClick={async () => {
                    setAiProviderBusy(true);
                    setAiProviderMessage("");
                    try {
                      const status = await invoke<AiProviderStatus>("remove_ai_provider_config");
                      setAiProviderStatus(status);
                      setAiProviderModel("");
                      setAiProviderKey("");
                      setAiProviderMessage("Saved provider credential removed. Restart JARVIS to apply the change.");
                    } catch {
                      setAiProviderMessage("JARVIS could not remove the saved provider credential.");
                    } finally {
                      setAiProviderBusy(false);
                    }
                  }}>Remove saved API key</button>
                </div>
              )}
            </article>
          </section>
        ) : active === "Memory" ? (
          <section className="projects-workspace">
            <div className="section-heading">
              <div><span className="eyebrow">SHARED WORKSPACE MEMORY</span><h2>Memory</h2></div>
              <button className="monitor-refresh" onClick={() => void refreshCloudMemory()} disabled={cloudMemoryBusy}>
                {cloudMemoryBusy ? "Loading…" : "Refresh memory"}
              </button>
            </div>
            <p className="monitor-intro">These entries are stored in your JARVIS cloud workspace and can be accessed by connected devices using the same account.</p>
            {!cloudSyncStatus?.connected && <div className="project-error">Connect the shared cloud workspace in Projects before using shared memory.</div>}
            <article className="panel-card">
              <div className="panel-title"><div><span className="eyebrow">ADD TO LONG-TERM CONTEXT</span><h3>Save a memory</h3></div><span className="tag">{cloudSyncStatus?.connected ? "CLOUD CONNECTED" : "OFFLINE"}</span></div>
              <form className="project-form" onSubmit={submitCloudMemory}>
                <label htmlFor="cloud-memory-category">Category</label>
                <select id="cloud-memory-category" value={cloudMemoryCategory} onChange={event => setCloudMemoryCategory(event.target.value as CloudMemoryRecord["category"])}>
                  <option value="fact">Fact</option><option value="preference">Preference</option><option value="decision">Decision</option><option value="note">Note</option><option value="reference">Reference</option>
                </select>
                <label htmlFor="cloud-memory-content">Memory</label>
                <textarea id="cloud-memory-content" required maxLength={10000} rows={4} value={cloudMemoryContent} onChange={event => setCloudMemoryContent(event.target.value)} placeholder="Write a useful fact, preference, decision or note…"/>
                <label htmlFor="cloud-memory-source">Source reference (optional)</label>
                <input id="cloud-memory-source" maxLength={2000} value={cloudMemorySource} onChange={event => setCloudMemorySource(event.target.value)} placeholder="Document, project or conversation reference"/>
                <div className="project-form-footer"><span>Only save information you want available across your connected JARVIS devices.</span><button type="submit" disabled={!cloudSyncStatus?.connected || cloudMemoryBusy || !cloudMemoryContent.trim()}>{cloudMemoryBusy ? "Saving…" : "Save memory"}</button></div>
              </form>
            </article>
            {cloudMemoryError && <div className="project-error">{cloudMemoryError}</div>}
            <div className="panel-card">
              <div className="panel-title"><div><span className="eyebrow">CLOUD RECORDS</span><h3>{cloudMemories.length} saved memories</h3></div></div>
              {cloudMemories.length === 0 ? <div className="projects-empty">No shared memories loaded yet. Refresh to retrieve entries from your workspace.</div> : cloudMemories.map(item => (
                <div className="activity-line" key={item.id}><span className="activity-dot done"/><div><b>{item.category.toUpperCase()}</b><small>{item.content}</small>{item.source_ref && <small>Source: {item.source_ref}</small>}</div><time>{new Date(item.created_at).toLocaleDateString()}</time></div>
              ))}
            </div>
          </section>
        ) : active === "Monitoring" ? (
          <section className="monitoring-workspace">
            <div className="section-heading">
              <div><span className="eyebrow">READ-ONLY CONNECTED SERVICES</span><h2>Monitoring centre</h2></div>
              <button className="monitor-refresh" onClick={() => setMonitoringRefreshKey(value => value + 1)}>Refresh status</button>
            </div>
            <p className="monitor-intro">JARVIS checks connected provider accounts using read-only API access. Tokens stay in the local gateway environment and are never shown here.</p>
            {monitoringLoading && <div className="projects-empty">Checking connected providers…</div>}
            {monitoringError && <div className="project-error">{monitoringError}</div>}
            <div className="monitor-provider-grid">
              {(monitoring?.providers ?? [
                { provider: "vercel", status: "not_configured" as const },
                { provider: "supabase", status: "not_configured" as const }
              ]).map(provider => (
                <article className="panel-card monitor-provider" key={provider.provider}>
                  <div className="panel-title"><div><span className="eyebrow">PROVIDER</span><h3>{provider.provider === "vercel" ? "Vercel" : "Supabase"}</h3></div><span className={`monitor-state ${provider.status}`}>{provider.status.replace("_", " ")}</span></div>
                  {provider.provider === "vercel" ? (
                    <div className="monitor-items">
                      {(provider.deployments ?? []).length ? provider.deployments!.map(item => <div className="monitor-item" key={item.id}><b>{item.name || item.url || "Deployment"}</b><span>{item.state} · {item.target || "environment not specified"}</span></div>) : <p className="muted">{provider.status === "not_configured" ? "Add a read-only VERCEL_TOKEN to the local gateway to inspect deployments." : provider.detail || "No deployments returned."}</p>}
                    </div>
                  ) : (
                    <div className="monitor-items">
                      {(provider.projects ?? []).length ? provider.projects!.map(item => <div className="monitor-item" key={item.ref}><b>{item.name}</b><span>{item.status} · {item.region}</span></div>) : <p className="muted">{provider.status === "not_configured" ? "Add a scoped read-only SUPABASE_ACCESS_TOKEN to inspect projects." : provider.detail || "No projects returned."}</p>}
                    </div>
                  )}
                </article>
              ))}
            </div>
            <div className="projects-note"><ShieldCheck size={14}/> Read-only overview only. JARVIS cannot deploy, change database settings or modify projects through this monitoring screen.</div>
          </section>
        ) : active === "Projects" ? (
          <section className="projects-workspace">
            <div className="section-heading">
              <div>
                <span className="eyebrow">YOUR LOCAL WORKSPACE</span>
                <h2>Projects</h2>
              </div>
              <span className="muted">{projects.length} saved {projects.length === 1 ? "project" : "projects"}</span>
            </div>
            <article className="panel-card cloud-sync-card">
              <div className="panel-title">
                <div><span className="eyebrow">CROSS-DEVICE WORKSPACE</span><h3>Connect your phone and Windows app</h3></div>
                <span className="tag">{cloudSyncStatus?.connected ? "CONNECTED" : "NOT CONNECTED"}</span>
              </div>
              <p className="panel-copy">
                Sign in with the same Supabase account configured in JARVIS Mobile. Your local desktop projects will be copied into the shared cloud workspace.
              </p>
              {cloudSyncStatus?.connected ? (
                <div className="cloud-sync-summary">
                  <b>{cloudSyncStatus.workspace_name}</b>
                  <span>{cloudSyncStatus.synced_projects} local projects synced to the shared workspace.</span>
                  <button type="button" disabled={cloudSyncBusy} onClick={syncCloudProjects}>
                    <Radio size={15}/>{cloudSyncBusy ? "Syncing…" : "Sync projects now"}
                  </button>
                  <button type="button" disabled={cloudSyncBusy} onClick={disconnectCloud}>
                    Disconnect
                  </button>
                </div>
              ) : (
                <form className="project-form" onSubmit={connectCloudAndSync}>
                  <label htmlFor="cloud-api-url">JARVIS Cloud API HTTPS URL</label>
                  <input id="cloud-api-url" type="url" required value={cloudApiUrl} onChange={event => setCloudApiUrl(event.target.value)} placeholder="https://your-jarvis-api.example.com"/>
                  <label htmlFor="cloud-supabase-url">Supabase project HTTPS URL</label>
                  <input id="cloud-supabase-url" type="url" required value={cloudSupabaseUrl} onChange={event => setCloudSupabaseUrl(event.target.value)} placeholder="https://your-project.supabase.co"/>
                  <label htmlFor="cloud-public-key">Supabase publishable / anon public key</label>
                  <input id="cloud-public-key" type="password" required value={cloudPublicKey} onChange={event => setCloudPublicKey(event.target.value)} autoComplete="off"/>
                  <label htmlFor="cloud-email">Account email</label>
                  <input id="cloud-email" type="email" required value={cloudEmail} onChange={event => setCloudEmail(event.target.value)} autoComplete="username"/>
                  <label htmlFor="cloud-password">Account password</label>
                  <input id="cloud-password" type="password" required value={cloudPassword} onChange={event => setCloudPassword(event.target.value)} autoComplete="current-password"/>
                  <div className="project-form-footer">
                    <span>The password is cleared from this form after submission. The cloud session stays in native memory for this app run and must be reconnected after restarting Windows JARVIS.</span>
                    <button type="submit" disabled={cloudSyncBusy}>
                      <ShieldCheck size={15}/>{cloudSyncBusy ? "Connecting…" : "Connect and sync"}
                    </button>
                  </div>
                </form>
              )}
              {cloudSyncError && <div className="project-error">{cloudSyncError}</div>}
              <p className="panel-copy">Use only the Supabase public client key here. Never enter a service-role or secret key. The first connection syncs project records only; tasks and other project history are not yet included.</p>
            </article>
            <div className="projects-layout">
              <article className="panel-card project-create-card">
                <div className="panel-title">
                  <div><span className="eyebrow">NEW WORKSPACE</span><h3>Create a project</h3></div>
                  <span className="tag">OWNER ONLY</span>
                </div>
                <p className="panel-copy">Keep a project’s purpose and status in JARVIS. Project records are stored locally on this device.</p>
                <form className="project-form" onSubmit={submitProject}>
                  <label htmlFor="project-name">Project name</label>
                  <input
                    id="project-name"
                    value={projectName}
                    onChange={event => setProjectName(event.target.value)}
                    maxLength={120}
                    placeholder="e.g. Drive Secure"
                    required
                  />
                  <label htmlFor="project-description">Description</label>
                  <textarea
                    id="project-description"
                    value={projectDescription}
                    onChange={event => setProjectDescription(event.target.value)}
                    maxLength={2000}
                    rows={4}
                    placeholder="What are you building?"
                  />
                  <div className="project-form-footer">
                    <span>{projectDescription.length}/2000</span>
                    <button type="submit" disabled={creatingProject || !projectName.trim()}>
                      <Sparkles size={15}/>{creatingProject ? "Saving…" : "Create project"}
                    </button>
                  </div>
                </form>
                {projectError && <div className="project-error">{projectError}</div>}
              </article>
              <article className="panel-card project-list-card">
                <div className="panel-title">
                  <div><span className="eyebrow">SAVED LOCALLY</span><h3>Your projects</h3></div>
                  <FolderKanban size={18}/>
                </div>
                {projectsLoading ? (
                  <div className="projects-empty">Loading your projects…</div>
                ) : projects.length === 0 ? (
                  <div className="projects-empty">
                    <div className="projects-empty-icon"><FolderKanban size={22}/></div>
                    <b>No projects yet</b>
                    <span>Create your first project to start building your JARVIS workspace.</span>
                  </div>
                ) : (
                  <div className="project-list">
                    {projects.map(project => (
                      <div className="project-entry" key={project.id}>
                        <div className="project-row">
                          <div className="project-symbol"><FolderKanban size={17}/></div>
                          <div className="project-main">
                            <b>{project.name}</b>
                            <span>{project.description || "No description added yet."}</span>
                            <small>Updated {new Date(project.updated_at * 1000).toLocaleDateString()}</small>
                            <button
                              type="button"
                              className="task-toggle"
                              onClick={() => void toggleProjectTasks(project.id)}
                            >
                              {activeTaskProjectId === project.id ? "Hide tasks" : "Manage tasks"}
                              <span>{(tasksByProject[project.id] ?? []).length}</span>
                            </button>
                          </div>
                          <select
                            className={`project-status-select ${project.status}`}
                            aria-label={`Status for ${project.name}`}
                            value={project.status}
                            disabled={updatingProjectId === project.id}
                            onChange={event => changeProjectStatus(
                              project.id,
                              event.target.value as Project["status"]
                            )}
                          >
                            <option value="active">Active</option>
                            <option value="paused">Paused</option>
                            <option value="completed">Completed</option>
                          </select>
                        </div>
                        {activeTaskProjectId === project.id && (
                          <div className="project-tasks-panel">
                            <div className="task-panel-heading">
                              <div><span className="eyebrow">PROJECT WORK</span><b>Tasks</b></div>
                              <span>{(tasksByProject[project.id] ?? []).length} saved</span>
                            </div>
                            <form className="task-create-form" onSubmit={event => void submitProjectTask(event, project.id)}>
                              <input
                                value={taskTitle}
                                onChange={event => setTaskTitle(event.target.value)}
                                maxLength={160}
                                placeholder="Add a task…"
                                aria-label={`New task for ${project.name}`}
                                required
                              />
                              <input
                                value={taskDescription}
                                onChange={event => setTaskDescription(event.target.value)}
                                maxLength={2000}
                                placeholder="Optional details"
                                aria-label="Task details"
                              />
                              <button type="submit" disabled={creatingTaskProjectId === project.id || !taskTitle.trim()}>
                                {creatingTaskProjectId === project.id ? "Adding…" : "Add task"}
                              </button>
                            </form>
                            {taskError && <div className="project-error">{taskError}</div>}
                            {tasksLoadingProjectId === project.id ? (
                              <div className="task-empty">Loading tasks…</div>
                            ) : (tasksByProject[project.id] ?? []).length === 0 ? (
                              <div className="task-empty">No tasks yet. Add the first action for this project.</div>
                            ) : (
                              <div className="task-list">
                                {(tasksByProject[project.id] ?? []).map(task => (
                                  <div className="task-row" key={task.id}>
                                    <div className="task-copy">
                                      <b>{task.title}</b>
                                      {task.description && <span>{task.description}</span>}
                                    </div>
                                    <select
                                      className={`task-status-select ${task.status}`}
                                      aria-label={`Status for task ${task.title}`}
                                      value={task.status}
                                      disabled={updatingTaskId === task.id}
                                      onChange={event => void changeProjectTaskStatus(
                                        project.id,
                                        task.id,
                                        event.target.value as ProjectTask["status"]
                                      )}
                                    >
                                      <option value="open">Open</option>
                                      <option value="in_progress">In progress</option>
                                      <option value="done">Done</option>
                                    </select>
                                  </div>
                                ))}
                              </div>
                            )}
                            <div className="project-activity">
                              <div className="task-panel-heading">
                                <div><span className="eyebrow">AUDIT TRAIL</span><b>Recent activity</b></div>
                                <span>{(activityByProject[project.id] ?? []).length} events</span>
                              </div>
                              {(activityByProject[project.id] ?? []).length === 0 ? (
                                <div className="task-empty">No project activity recorded yet.</div>
                              ) : (
                                <div className="project-activity-list">
                                  {(activityByProject[project.id] ?? []).slice(0, 8).map(item => (
                                    <div className="project-activity-row" key={item.id}>
                                      <span className="activity-dot done"/>
                                      <div>
                                        <b>{item.event_type.replace(/[._]/g, " ")}</b>
                                        <small>{item.entity_type} · {new Date(item.occurred_at * 1000).toLocaleString()}</small>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="project-milestones">
                              <div className="task-panel-heading">
                                <div><span className="eyebrow">DELIVERY PLAN</span><b>Milestones</b></div>
                                <span>{(milestonesByProject[project.id] ?? []).length} tracked</span>
                              </div>
                              <form
                                className="milestone-create-form"
                                onSubmit={event => void submitProjectMilestone(event, project.id)}
                              >
                                <input
                                  value={milestoneTitle}
                                  onChange={event => setMilestoneTitle(event.target.value)}
                                  maxLength={160}
                                  placeholder="Milestone title"
                                  aria-label="Milestone title"
                                  required
                                />
                                <input
                                  value={milestoneDescription}
                                  onChange={event => setMilestoneDescription(event.target.value)}
                                  maxLength={2000}
                                  placeholder="Short description (optional)"
                                  aria-label="Milestone description"
                                />
                                <label htmlFor={`milestone-date-${project.id}`}>Target date</label>
                                <input
                                  id={`milestone-date-${project.id}`}
                                  type="date"
                                  value={milestoneTargetDate}
                                  onChange={event => setMilestoneTargetDate(event.target.value)}
                                />
                                <button type="submit" disabled={savingMilestoneProjectId === project.id || !milestoneTitle.trim()}>
                                  {savingMilestoneProjectId === project.id ? "Saving…" : "Add milestone"}
                                </button>
                              </form>
                              {(milestonesByProject[project.id] ?? []).length === 0 ? (
                                <div className="task-empty">No milestones defined for this project yet.</div>
                              ) : (
                                <div className="milestone-list">
                                  {(milestonesByProject[project.id] ?? []).map(item => (
                                    <div className="milestone-row" key={item.id}>
                                      <div className="milestone-copy">
                                        <b>{item.title}</b>
                                        {item.description && <span>{item.description}</span>}
                                        {item.target_at !== null && (
                                          <small>Target {new Date(item.target_at * 1000).toLocaleDateString()}</small>
                                        )}
                                        {item.completed_at !== null && (
                                          <small>Completed {new Date(item.completed_at * 1000).toLocaleDateString()}</small>
                                        )}
                                      </div>
                                      <select
                                        className={`milestone-status-select ${item.status}`}
                                        aria-label={`Status for milestone ${item.title}`}
                                        value={item.status}
                                        disabled={updatingMilestoneId === item.id}
                                        onChange={event => void changeProjectMilestoneStatus(
                                          project.id,
                                          item.id,
                                          event.target.value as ProjectMilestone["status"]
                                        )}
                                      >
                                        <option value="planned">Planned</option>
                                        <option value="in_progress">In progress</option>
                                        <option value="completed">Completed</option>
                                        <option value="cancelled">Cancelled</option>
                                      </select>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="project-decisions">
                              <div className="task-panel-heading">
                                <div><span className="eyebrow">RISK MANAGEMENT</span><b>Project risk register</b></div>
                                <span>{(risksByProject[project.id] ?? []).length} tracked</span>
                              </div>
                              <form className="decision-create-form" onSubmit={event => void submitProjectRisk(event, project.id)}>
                                <input value={riskTitle} onChange={event => setRiskTitle(event.target.value)} maxLength={160} placeholder="Risk title" required />
                                <textarea value={riskDescription} onChange={event => setRiskDescription(event.target.value)} maxLength={2000} rows={2} placeholder="Describe the risk" />
                                <select value={riskSeverity} onChange={event => setRiskSeverity(event.target.value as ProjectRisk["severity"])} aria-label="Risk severity">
                                  <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
                                </select>
                                <input value={riskMitigation} onChange={event => setRiskMitigation(event.target.value)} maxLength={2000} placeholder="Mitigation plan (optional)" />
                                <button type="submit" disabled={!riskTitle.trim()}>Add risk</button>
                              </form>
                              {(risksByProject[project.id] ?? []).length === 0 ? <div className="task-empty">No risks recorded.</div> : (
                                <div className="milestone-list">
                                  {(risksByProject[project.id] ?? []).map(item => (
                                    <div className="milestone-row" key={item.id}>
                                      <div className="milestone-copy"><b>{item.title} · {item.severity}</b>{item.description && <span>{item.description}</span>}{item.mitigation && <small>Mitigation: {item.mitigation}</small>}</div>
                                      <select value={item.status} aria-label={`Status for risk ${item.title}`} onChange={event => void changeProjectRiskStatus(project.id, item.id, event.target.value as ProjectRisk["status"])}>
                                        <option value="open">Open</option><option value="mitigated">Mitigated</option><option value="accepted">Accepted</option><option value="closed">Closed</option>
                                      </select>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="project-decisions">
                              <div className="task-panel-heading">
                                <div><span className="eyebrow">PERSISTENT PROJECT BRAIN</span><b>Project memory</b></div>
                                <span>{(memoryByProject[project.id] ?? []).length} entries</span>
                              </div>
                              <form className="decision-create-form" onSubmit={event => void submitProjectMemory(event, project.id)}>
                                <select value={memoryCategory} onChange={event => setMemoryCategory(event.target.value as ProjectMemory["category"])} aria-label="Memory category">
                                  <option value="fact">Fact</option><option value="preference">Preference</option><option value="decision">Decision</option><option value="note">Note</option><option value="reference">Reference</option>
                                </select>
                                <textarea value={memoryContent} onChange={event => setMemoryContent(event.target.value)} maxLength={4000} rows={3} placeholder="Record a useful project fact, preference, note or reference" required />
                                <input value={memorySourceRef} onChange={event => setMemorySourceRef(event.target.value)} maxLength={1000} placeholder="Source reference (optional)" />
                                <button type="submit" disabled={!memoryContent.trim()}>Save memory</button>
                              </form>
                              {(memoryByProject[project.id] ?? []).length === 0 ? <div className="task-empty">No persistent memory entries yet.</div> : (
                                <div className="project-decision-list">
                                  {(memoryByProject[project.id] ?? []).map(item => (
                                    <details className="project-decision-item" key={item.id}>
                                      <summary><b>{item.category}</b><small>{new Date(item.created_at * 1000).toLocaleDateString()}</small></summary>
                                      <p>{item.content}</p>{item.source_ref && <small className="decision-source">Source: {item.source_ref}</small>}
                                    </details>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="project-decisions">
                              <div className="task-panel-heading">
                                <div><span className="eyebrow">SECURITY CONTROL</span><b>Action approvals</b></div>
                                <span>{(approvalsByProject[project.id] ?? []).filter(item => item.status === "pending").length} awaiting review</span>
                              </div>
                              <form className="decision-create-form" onSubmit={event => void submitProjectApproval(event, project.id)}>
                                <input value={approvalAction} onChange={event => setApprovalAction(event.target.value)} maxLength={120} aria-label="Action identifier" placeholder="Action identifier" required />
                                <textarea value={approvalArguments} onChange={event => setApprovalArguments(event.target.value)} rows={3} aria-label="Exact action arguments in JSON" placeholder="Exact action arguments as JSON" required />
                                <button type="submit" disabled={!approvalAction.trim()}>Request approval</button>
                              </form>
                              {(approvalsByProject[project.id] ?? []).length === 0 ? <div className="task-empty">No approval requests recorded.</div> : (
                                <div className="project-decision-list">
                                  {(approvalsByProject[project.id] ?? []).map(item => (
                                    <details className="project-decision-item" key={item.id}>
                                      <summary><b>{item.action}</b><small>{item.status.replace("_", " ")}</small></summary>
                                      <pre>{JSON.stringify(item.arguments, null, 2)}</pre>
                                      <small className="decision-source">Expires: {new Date(item.expires_at * 1000).toLocaleString()}</small>
                                      {item.status === "pending" && (
                                        <div className="approval-actions">
                                          <button type="button" disabled={approvalBusyId === item.id} onClick={() => void reviewProjectApproval(project.id, item.id, true)}>Approve</button>
                                          <button type="button" disabled={approvalBusyId === item.id} onClick={() => void reviewProjectApproval(project.id, item.id, false)}>Reject</button>
                                        </div>
                                      )}
                                      {item.status === "approved" && item.action === "project.task.create" && (
                                        <div className="approval-actions">
                                          <button type="button" disabled={approvalBusyId === item.id} onClick={() => void executeApprovedTask(project.id, item)}>{approvalBusyId === item.id ? "Executing…" : "Execute approved task"}</button>
                                        </div>
                                      )}
                                    </details>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="project-decisions">
                              <div className="task-panel-heading">
                                <div><span className="eyebrow">PROJECT MEMORY</span><b>Decision journal</b></div>
                                <span>{(decisionsByProject[project.id] ?? []).length} recorded</span>
                              </div>
                              <form
                                className="decision-create-form"
                                onSubmit={event => void submitProjectDecision(event, project.id)}
                              >
                                <input
                                  value={decisionTitle}
                                  onChange={event => setDecisionTitle(event.target.value)}
                                  maxLength={160}
                                  placeholder="Decision title"
                                  aria-label="Decision title"
                                  required
                                />
                                <textarea
                                  value={decisionText}
                                  onChange={event => setDecisionText(event.target.value)}
                                  maxLength={4000}
                                  rows={3}
                                  placeholder="What was decided?"
                                  aria-label="Decision"
                                  required
                                />
                                <textarea
                                  value={decisionRationale}
                                  onChange={event => setDecisionRationale(event.target.value)}
                                  maxLength={4000}
                                  rows={2}
                                  placeholder="Why was this chosen? (optional)"
                                  aria-label="Decision rationale"
                                />
                                <input
                                  value={decisionSourceRef}
                                  onChange={event => setDecisionSourceRef(event.target.value)}
                                  maxLength={1000}
                                  placeholder="Source or reference (optional)"
                                  aria-label="Decision source reference"
                                />
                                <button type="submit" disabled={savingDecisionProjectId === project.id || !decisionTitle.trim() || !decisionText.trim()}>
                                  {savingDecisionProjectId === project.id ? "Recording…" : "Record decision"}
                                </button>
                              </form>
                              {(decisionsByProject[project.id] ?? []).length === 0 ? (
                                <div className="task-empty">No decisions recorded for this project yet.</div>
                              ) : (
                                <div className="project-decision-list">
                                  {(decisionsByProject[project.id] ?? []).map(item => (
                                    <details className="project-decision-item" key={item.id}>
                                      <summary>
                                        <b>{item.title}</b>
                                        <small>{new Date(item.decided_at * 1000).toLocaleDateString()}</small>
                                      </summary>
                                      <p>{item.decision}</p>
                                      {item.rationale && <p><strong>Rationale:</strong> {item.rationale}</p>}
                                      {item.source_ref && <small className="decision-source">Source: {item.source_ref}</small>}
                                    </details>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </article>
            </div>
            <div className="projects-note"><ShieldCheck size={14}/> Project access is checked by the local gateway using your signed-in owner session. The interface cannot choose or change project ownership.</div>
          </section>
        ) : (
          <>
            <div className="section-heading"><div><span className="eyebrow">CONTROL CENTRE</span><h2>{active === "Overview" ? "System overview" : active}</h2></div><span className="muted">Private deployment · Local-first design</span></div>
            <div className="metric-grid">
              <article className="metric-card"><div className="metric-icon violet"><FolderKanban size={18}/></div><span>PROJECTS</span><strong>{projects.length} saved</strong><small>Locally stored workspaces</small></article>
              <article className="metric-card"><div className="metric-icon blue"><TerminalSquare size={18}/></div><span>ENGINEERING</span><strong>Foundation</strong><small>Build · Test · Review</small></article>
              <article className="metric-card"><div className="metric-icon green"><ShieldCheck size={18}/></div><span>SECURITY</span><strong>{capabilities?.security.gateway_session_configured ? "Session protected" : capabilitiesError ? "Bridge unavailable" : "Checking session"}</strong><small>{capabilities?.security.owner_session_authenticated ? "Owner session verified" : "Local owner account configured"}</small></article>
              <article className="metric-card"><div className="metric-icon amber"><Radio size={18}/></div><span>MONITORING</span><strong>Not connected</strong><small>No background checks yet</small></article>
            </div>
            <LiveWorkspace onOpenProjects={() => setActive("Projects")}/>
            <div className="lower-grid"><article className="panel-card activity-card"><div className="panel-title"><div><span className="eyebrow">SYSTEM ACTIVITY</span><h3>Build status</h3></div><Activity size={17}/></div><div className="activity-line"><span className="activity-dot done"/><div><b>Product specification</b><small>Master PRD and system boundaries committed</small></div><time>DONE</time></div><div className="activity-line"><span className="activity-dot done"/><div><b>Architecture & security</b><small>Data model, threat model and standards committed</small></div><time>DONE</time></div><div className="activity-line"><span className="activity-dot current"/><div><b>Application foundation</b><small>Desktop shell and authenticated local gateway</small></div><time>NOW</time></div><div className="activity-line"><span className="activity-dot"/><div><b>Agent orchestration</b><small>Queued behind persistent project state</small></div><time>QUEUED</time></div></article></div>
          </>
        )}
        <footer><span>JARVIS · PRIVATE AI OPERATING ENVIRONMENT</span><span><MonitorUp size={13}/> Desktop build · Early foundation</span></footer>
      </div>
    </section>
  </main>;
}
