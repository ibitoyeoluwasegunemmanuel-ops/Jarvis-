import { FormEvent, useEffect, useState } from "react";
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
  Sparkles,
  TerminalSquare
} from "lucide-react";

type Health = { status: string; service?: string; version?: string };
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

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [capabilities, setCapabilities] = useState<GatewayCapabilities | null>(null);
  const [capabilitiesError, setCapabilitiesError] = useState(false);
  const [authStatus, setAuthStatus] = useState<OwnerAuthStatus | null>(null);
  const [nativeUnavailable, setNativeUnavailable] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authBusy, setAuthBusy] = useState(false);
  const [active, setActive] = useState("Overview");
  const [message, setMessage] = useState("");
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectError, setProjectError] = useState("");
  const [projectName, setProjectName] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  const [updatingProjectId, setUpdatingProjectId] = useState<string | null>(null);
  const [activeTaskProjectId, setActiveTaskProjectId] = useState<string | null>(null);
  const [tasksByProject, setTasksByProject] = useState<Record<string, ProjectTask[]>>({});
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
      setMessage("");
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

  const changeProjectStatus = async (projectId: string, status: Project["status"]) => {
    setUpdatingProjectId(projectId);
    setProjectError("");
    try {
      const updated = await invoke<Project>("update_project_status", {
        projectId,
        status
      });
      setProjects(current => current.map(item => item.id === updated.id ? updated : item));
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
    if (tasksByProject[projectId]) return;

    setTasksLoadingProjectId(projectId);
    try {
      const tasks = await invoke<ProjectTask[]>("list_project_tasks", { projectId });
      setTasksByProject(current => ({ ...current, [projectId]: tasks }));
    } catch (error) {
      const detail = String(error);
      if (detail.includes("owner_session_expired") || detail.includes("owner_session_required")) {
        setAuthStatus(current => current ? { ...current, authenticated: false } : current);
      }
      setTaskError("JARVIS could not load tasks for this project.");
    } finally {
      setTasksLoadingProjectId(null);
    }
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

  const nav = [
    { label: "Overview", icon: LayoutDashboard },
    { label: "Projects", icon: FolderKanban },
    { label: "AI Workspace", icon: BrainCircuit },
    { label: "Engineering", icon: TerminalSquare },
    { label: "Security", icon: ShieldCheck },
    { label: "Analytics", icon: Activity }
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
        {active === "Projects" ? (
          <section className="projects-workspace">
            <div className="section-heading">
              <div>
                <span className="eyebrow">YOUR LOCAL WORKSPACE</span>
                <h2>Projects</h2>
              </div>
              <span className="muted">{projects.length} saved {projects.length === 1 ? "project" : "projects"}</span>
            </div>
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
            <div className="lower-grid"><article className="panel-card"><div className="panel-title"><div><span className="eyebrow">COMMAND INTERFACE</span><h3>What are we working on?</h3></div><span className="tag">TEXT MODE</span></div><p className="panel-copy">Owner authentication and local project storage are active. Task execution and specialist agents are not connected yet.</p><div className="composer"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="Describe a task…" aria-label="Task description" /><button disabled={!message.trim()} onClick={() => setMessage("")}><Sparkles size={16}/> Clear draft</button></div><div className="hint"><Mic size={14}/> Voice input will be enabled after realtime session and permission controls are implemented.</div></article>
            <article className="panel-card activity-card"><div className="panel-title"><div><span className="eyebrow">SYSTEM ACTIVITY</span><h3>Build status</h3></div><Activity size={17}/></div><div className="activity-line"><span className="activity-dot done"/><div><b>Product specification</b><small>Master PRD and system boundaries committed</small></div><time>DONE</time></div><div className="activity-line"><span className="activity-dot done"/><div><b>Architecture & security</b><small>Data model, threat model and standards committed</small></div><time>DONE</time></div><div className="activity-line"><span className="activity-dot current"/><div><b>Application foundation</b><small>Desktop shell and authenticated local gateway</small></div><time>NOW</time></div><div className="activity-line"><span className="activity-dot"/><div><b>Agent orchestration</b><small>Queued behind persistent project state</small></div><time>QUEUED</time></div></article></div>
          </>
        )}
        <footer><span>JARVIS · PRIVATE AI OPERATING ENVIRONMENT</span><span><MonitorUp size={13}/> Desktop build · Early foundation</span></footer>
      </div>
    </section>
  </main>;
}
