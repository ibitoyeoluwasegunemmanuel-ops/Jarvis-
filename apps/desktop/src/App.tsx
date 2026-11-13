import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Activity, AudioLines, BrainCircuit, ChevronRight, CircleHelp, Command, FolderKanban, LayoutDashboard, Mic, MonitorUp, Radio, ShieldCheck, Sparkles, TerminalSquare } from "lucide-react";

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
  };
};
const gateway = import.meta.env.VITE_GATEWAY_URL ?? "http://127.0.0.1:8765";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [capabilities, setCapabilities] = useState<GatewayCapabilities | null>(null);
  const [capabilitiesError, setCapabilitiesError] = useState(false);
  const [active, setActive] = useState("Overview");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    let retryTimer: number | undefined;
    let capabilitiesLoaded = false;

    const checkGateway = async () => {
      try {
        const response = await fetch(`${gateway}/health`, {
          signal: controller.signal
        });
        if (!response.ok) throw new Error("Gateway unavailable");
        setHealth(await response.json() as Health);
        setHealthError(false);

        // This typed Tauri command attaches the session header natively.
        // The secret is never returned to this React component.
        if (!capabilitiesLoaded) {
          try {
            const result = await invoke<GatewayCapabilities>("get_gateway_capabilities");
            if (!controller.signal.aborted) {
              setCapabilities(result);
              setCapabilitiesError(false);
              capabilitiesLoaded = true;
            }
          } catch {
            if (!controller.signal.aborted) setCapabilitiesError(true);
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

  const nav = [
    { label: "Overview", icon: LayoutDashboard },
    { label: "Projects", icon: FolderKanban },
    { label: "AI Workspace", icon: BrainCircuit },
    { label: "Engineering", icon: TerminalSquare },
    { label: "Security", icon: ShieldCheck },
    { label: "Analytics", icon: Activity }
  ];

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Sparkles size={19}/></div><div><strong>JARVIS</strong><span>PERSONAL AI SYSTEM</span></div></div>
      <div className="workspace-label">WORKSPACE</div>
      <nav>{nav.map(item => <button key={item.label} className={active === item.label ? "nav-item active" : "nav-item"} onClick={() => setActive(item.label)}><item.icon size={17}/><span>{item.label}</span>{active === item.label && <ChevronRight size={15}/>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="secure-pill"><ShieldCheck size={15}/> Private workspace</div><div className="profile"><div className="avatar-mini">C</div><div><b>CEO Global</b><span>Owner access</span></div><CircleHelp size={17}/></div></div>
    </aside>
    <section className="main-panel">
      <header className="topbar"><div className="breadcrumb">JARVIS <span>/</span> {active}</div><div className="top-actions"><span className={health?.status === "ok" ? "status online" : "status"}><i/> {health?.status === "ok" ? "Gateway connected" : healthError ? "Gateway offline" : "Connecting…"}</span><button className="icon-button" aria-label="Command menu"><Command size={17}/></button></div></header>
      <div className="content">
        <div className="welcome-row"><div><div className="eyebrow"><span className="pulse"/> SYSTEM INITIALISING</div><h1>Your workspace.<br/><em>One intelligent system.</em></h1><p className="lead">A unified environment for building, analysing, researching and operating your projects.</p></div><div className="presence-card"><div className="presence-orb"><AudioLines size={27}/></div><div><b>JARVIS presence</b><span>Voice interface is being prepared</span></div><span className="coming">IN DEVELOPMENT</span></div></div>
        <div className="section-heading"><div><span className="eyebrow">CONTROL CENTRE</span><h2>{active === "Overview" ? "System overview" : active}</h2></div><span className="muted">Private deployment · Local-first design</span></div>
        <div className="metric-grid">
          <article className="metric-card"><div className="metric-icon violet"><BrainCircuit size={18}/></div><span>PROJECT MEMORY</span><strong>Preparing</strong><small>Persistent context layer</small></article>
          <article className="metric-card"><div className="metric-icon blue"><TerminalSquare size={18}/></div><span>ENGINEERING</span><strong>Planned</strong><small>Build · Test · Review</small></article>
          <article className="metric-card"><div className="metric-icon green"><ShieldCheck size={18}/></div><span>SECURITY</span><strong>{capabilities?.security.gateway_session_configured ? "Session protected" : capabilitiesError ? "Bridge unavailable" : "Checking session"}</strong><small>{capabilities?.security.gateway_session_configured ? "Native token stays outside the webview" : "Owner login and workspace auth are not ready"}</small></article>
          <article className="metric-card"><div className="metric-icon amber"><Radio size={18}/></div><span>MONITORING</span><strong>Not connected</strong><small>No background checks yet</small></article>
        </div>
        <div className="lower-grid"><article className="panel-card"><div className="panel-title"><div><span className="eyebrow">COMMAND INTERFACE</span><h3>What are we working on?</h3></div><span className="tag">TEXT MODE</span></div><p className="panel-copy">The native bridge now reads gateway capability and session status without exposing its secret to the interface. Task execution and specialist agents are not connected yet.</p><div className="composer"><input value={message} onChange={e => setMessage(e.target.value)} placeholder="Describe a task…" aria-label="Task description" /><button disabled={!message.trim()} onClick={() => setMessage("")}><Sparkles size={16}/> Clear draft</button></div><div className="hint"><Mic size={14}/> Voice input will be enabled after realtime session and permission controls are implemented.</div></article>
        <article className="panel-card activity-card"><div className="panel-title"><div><span className="eyebrow">SYSTEM ACTIVITY</span><h3>Build status</h3></div><Activity size={17}/></div><div className="activity-line"><span className="activity-dot done"/><div><b>Product specification</b><small>Master PRD and system boundaries committed</small></div><time>DONE</time></div><div className="activity-line"><span className="activity-dot done"/><div><b>Architecture & security</b><small>Data model, threat model and standards committed</small></div><time>DONE</time></div><div className="activity-line"><span className="activity-dot current"/><div><b>Application foundation</b><small>Desktop shell and local gateway scaffold</small></div><time>NOW</time></div><div className="activity-line"><span className="activity-dot"/><div><b>Agent orchestration</b><small>Shared tool contracts and permission engine</small></div><time>QUEUED</time></div></article></div>
        <footer><span>JARVIS · PRIVATE AI OPERATING ENVIRONMENT</span><span><MonitorUp size={13}/> Desktop build · Early foundation</span></footer>
      </div>
    </section>
  </main>;
}