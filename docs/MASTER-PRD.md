# JARVIS — Master Product Requirements Document

Status: Baseline product specification  
Product owner: Ibitoye Oluwasegun Emmanuel  
Initial deployment: Private, single-owner desktop installation  
Long-term direction: Secure multi-user platform for founders and technical teams

## 1. Vision
JARVIS is a persistent AI operating environment that converses naturally, sees what the user explicitly shares, works in a shared visual workspace, understands ongoing projects, uses approved tools, and completes multi-step work with verification.

It is not merely a chatbot, animated avatar, voice wrapper, or collection of unrelated automations. Avatar, voice, reasoning, memory, workspace, tools, and security policy form one coordinated product.

The intended experience is a cinematic virtual office: a realistic human-like assistant appears present, speaks naturally, listens, responds with expressions and lip movement, and can bring research, diagrams, documents, code, browser pages, and project status onto a shared screen.

## 2. Product outcomes
JARVIS helps its owner:
- Build, review, debug, test, secure, and deploy software.
- Research technology, vendors, markets, regulations, and public information.
- Analyse datasets, spreadsheets, databases, business performance, and trends.
- Plan and coordinate multiple ventures and technical projects.
- Create and critique interfaces, graphics, presentations, diagrams, and media briefs.
- Inspect user-shared screenshots, documents, camera images, and screen sessions.
- Operate approved desktop and browser workflows with visibility and control.
- Detect project blockers and surface configurable briefings.
- Draft communications and prepare actions for approval.

Success is measured by completed and verified outcomes, not confident-sounding responses.

## 3. Users and deployment
### Initial user
One owner using a Windows desktop. The installer detects supported Windows version and hardware capabilities; the user should not need to know whether the machine runs Windows 10 or 11. Actual OS support must be confirmed against current runtime requirements.

### Future users
Founders, operators, developers, analysts, and small teams. Tenant boundaries and role-based access are designed from the beginning, without adding unnecessary enterprise administration to the private pilot.

### Locale and accessibility
- English-first, with deliberate Nigerian English speech evaluation.
- Configurable voice, speed, captions, push-to-talk, and keyboard alternatives.
- Text fallback for noisy environments.
- Configurable timezone, date, currency, and regional formats.

## 4. Experience requirements
### 4.1 Virtual presence and avatar
- Realistic 3D human avatar with selectable appearance/presentation.
- Idle, listening, thinking, speaking, and interrupted states.
- Eye movement, blinking, head motion, facial expressions, and lip-sync.
- Avatar can be hidden; compact workspace remains fully functional.
- Commercially licensed assets and voices only.
- Rendering must not block core operation on lower-powered devices.

Acceptance: responsive state transitions, measured speech/viseme synchronisation, and a usable non-avatar fallback.

### 4.2 Voice conversation
- Low-latency streaming speech.
- Barge-in: user interruption promptly stops playback and current speech generation.
- Push-to-talk by default; wake word is optional and explicitly enabled.
- Always-visible microphone state, live captions, and editable transcript.
- Nigerian English evaluation using consented test utterances.
- Provider adapters prevent vendor lock-in.
- Graceful text fallback during network/provider failure.

Acceptance: measured end-to-end latency, interruption latency, speech recognition quality, and user-rated voice quality.

### 4.3 Vision and user-shared context
- Explicit screen/window sharing and screenshot, image, PDF, and document upload.
- Camera capture/session starts only on user command and is visibly indicated.
- Inspect UI, read error messages, explain objects, and reason over supplied documents.
- Immediate pause/stop controls.
- No background or covert camera/screen capture.
- Visual findings link to source image/page where possible.

Acceptance: distinguish observation from inference; ask for a clearer capture when evidence is insufficient.

### 4.4 Shared workspace
Panels for browser pages and sources; code, diffs, tests and terminal output; documents, spreadsheets, charts and diagrams; project boards and timelines; annotated screenshots; agent plans, progress and verification. Displayed data must be attributable to a source, project, or current task.

## 5. Intelligence and specialist capabilities
A central orchestrator routes work to specialist agents. All specialists share policy, memory, tool contracts, and audit infrastructure; no specialist is an unrestricted independent bot.

### 5.1 Full-stack engineering
Requirements, architecture, frontend, backend, APIs, mobile, databases, infrastructure, code search, implementation, refactoring, migrations, debugging, tests, CI/CD, deployment preparation, code review, accessibility, reliability, and documentation. Report exact files changed, tests run, failures, and unverified assumptions.

### 5.2 Cybersecurity and defensive security
Threat modelling, secure architecture and coding review, dependency/configuration/secret analysis, authorised defensive assessments, risk prioritisation, incident triage, evidence preservation, remediation and retesting. Never claim security from a superficial scan. Refuse credential theft, malware, stealth, persistence, evasion, unauthorised intrusion, or surveillance.

### 5.3 Data analysis and analytics
CSV/XLSX/JSON/SQL ingestion; schema and quality checks; cleaning, deduplication, transformations; reproducible analysis; SQL generation/review; descriptive and inferential statistics; forecasting, segmentation, scenario analysis, dashboards and charts. Report data lineage, missingness, outliers, assumptions, and uncertainty. Distinguish correlation from causation.

### 5.4 Technology research
Compare frameworks, APIs, devices, vendors, cloud services, pricing, compatibility, licensing, and security posture. Prefer current primary documentation, dated source links, evidence quality, and explicit uncertainty.

### 5.5 Product, UX, and creative
Product discovery, user journeys, requirements, wireframes, UI critique, design systems, graphics, diagrams, brand concepts, presentations, and image/video briefs. Include accessibility, responsiveness, consistency, and handoff checks. State when final specialist design polish is advisable.

### 5.6 Business and operations
Project plans, milestones, risk registers, meeting notes, decisions, action items, unit economics, pricing, forecasts, dashboards, reports, proposals, and outreach drafts. No outbound communication or financial commitment without approval.

### 5.7 Research and fraud analysis
Research public information about organisations, products, public events, and markets. Analyse user-submitted messages, URLs, invoices, and offers for scam indicators. Present evidence and red flags, not unsupported declarations of guilt. No doxxing, private-person profiling, or unauthorised personal-data collection.

## 6. Project brain and memory
Maintain structured project context, not merely a transcript archive. Project records include name, purpose, owner, status, priority, stakeholders, repository, environments, requirements, architecture decisions, risks, milestones, tasks, dependencies, last verified state, evidence, tests, deployments, documents, and next action.

Memory categories:
1. Explicit user-approved facts and preferences.
2. Project facts with source and last-verified timestamp.
3. Decisions and rationale.
4. Episodic task/conversation history.
5. Derived semantic memory with confidence and provenance.

Users can inspect, correct, export, and delete memory. Distinguish stored fact, current observation, inference, and stale information. Never silently promote a memory into a high-impact action.

Initial configurable project seeds may include DiasporaOS, Drive Secure, HANDLY, PPOINT, SellLive, CareLink Africa, Sendly, Soko, and WorldScope News. This is not a fixed enum.

## 7. Computer and browser operation
Open approved applications and browser sessions; navigate, search, click, type, scroll, download/upload where permitted; inspect page state; work in approved project folders and repositories; run allowlisted developer tools in restricted workspaces; edit files, test, and prepare commits or pull requests.

Controls include a visible operator-active indicator, per-session scope, immediate stop, allowlisted directories/domains/executables, isolated browser contexts, and approval for consequential actions. Destructive actions require confirmation and a recovery plan where feasible.

## 8. Integrations
Initial candidates: GitHub, Gmail, Calendar, Drive, Supabase/Postgres, browser automation, and local files.

Use scoped OAuth where supported; never request long-lived passwords in chat. Store tokens encrypted. Expose connection status, granted scopes, last sync, revoke/disconnect. Draft-first communication: sending, posting, sharing, publishing, or inviting requires approval.

## 9. Proactive intelligence and monitoring
Configurable daily/weekly briefings; project health, task deadlines, build/deployment failures, integration alerts. Monitor only explicitly configured repositories, projects, inbox labels, calendars, or sources. Show scope, frequency, data accessed, and last check. Quiet hours and thresholds are user-controlled. Do not claim continuous monitoring while app/service is offline or disconnected. Alerts include evidence, timestamp, confidence, and suggested action.

## 10. Modes
Conversation, Focus, Build, Research, Analyse, Operate, Briefing, and Studio. These are views over one orchestrated system, not separate products.

## 11. Trust, privacy, and approvals
Visible microphone/camera/screen/operator indicators; explicit capture start/stop; encryption in transit and at rest; least privilege and tenant isolation; secret redaction; auditable approvals; configurable retention, export and deletion. No hidden recording or unapproved data resale.

Production deployment, payments, financial transfers, external publication, deletion, permission changes, and messages require explicit approval. Approval binds to exact action, target, and parameters; changed parameters require renewed approval.

## 12. Non-functional requirements
Reliability across provider/network failures; streaming progress; measurable performance; threat modelling and security CI; structured logs/traces/metrics; typed contracts; versioned migrations; accessible keyboard and captions; local-first desktop core; usage budgets and cost visibility.

## 13. Acceptance gates
Each capability must pass functional and failure-path tests, permission/denial tests, tenant isolation, evidence-based verification, owner usability review, performance/cost measurement, and recovery documentation. Critical security defects, exposed secrets, unbounded tool access, unapproved outbound actions, or misleading success reporting block release.

## 14. Non-goals and boundaries
No autonomous financial transfers or trading; no covert device/account access; no unauthorised penetration testing; no private-person surveillance; no guarantee of perfect accuracy or autonomous delivery; no claim of consciousness or physical presence.

## 15. Decisions requiring evidence
Realtime voice provider and Nigerian English quality; avatar provider and licensing; cloud/local inference split and hardware; hosting region/data residency; supported Windows baseline; pilot integrations; cost ceilings. Document options, evidence, cost, risks, decision, and review date.
