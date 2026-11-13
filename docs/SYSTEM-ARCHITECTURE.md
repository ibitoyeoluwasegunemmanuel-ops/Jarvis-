# JARVIS — System Architecture

Status: Proposed reference architecture. Validate through prototypes, threat modelling, and measured tests.

## 1. Principles
- One orchestrated system with consistent identity, policy, memory, and audit.
- Separate user interface, orchestration, tools, and privileged local operations.
- Explicit contracts and provider adapters.
- Local computer access isolated in a small, inspectable operator.
- Model output is an untrusted proposal, never authority to bypass policy.
- Every external action has an execution record and verifiable result.

## 2. Logical topology

```text
Desktop App (Tauri + React)
  ├── Virtual Office / 3D Avatar
  ├── Voice + Captions + Vision Share UI
  ├── Shared Workspace / Project Console
  └── Permission + Approval UI
          │ authenticated IPC / HTTPS
          ▼
JARVIS Local Gateway (FastAPI)
  ├── Session & Identity
  ├── Orchestrator / Planner
  ├── Policy & Approval Engine
  ├── Memory / Project Context
  ├── Tool Registry & Execution Router
  ├── Observability / Audit
  └── Local Operator Supervisor
       ├── Browser Worker (Playwright)
       ├── Filesystem Worker (scoped roots)
       └── Developer Worker (allowlisted commands)
          │
          ├── Model Provider Adapters
          ├── Realtime Voice / ASR / TTS Adapters
          ├── Avatar Runtime / Asset Loader
          ├── Vision / OCR / Document Pipeline
          ├── Analytics Runtime
          └── Integration Adapters (GitHub, Google, Supabase)
          │
          ▼
Data Layer
  ├── PostgreSQL + pgvector
  ├── Encrypted object storage
  ├── Local encrypted cache
  └── Optional queue / job runner
```

## 3. Component responsibilities
### Desktop shell
Tauri 2 + React + TypeScript owns presentation, session UX, keyboard shortcuts, notifications, secure IPC, and app lifecycle. Native permissions are explicit. Never expose unrestricted shell or filesystem APIs to the webview.

### Avatar and workspace
Three.js scene with licensed GLB/GLTF character, facial blend shapes, visemes, animation state machine, and compact fallback. Workspace panels display browser, code, docs, charts, project board, and activity feed. Avatar is replaceable and not coupled to reasoning.

### Voice session manager
Owns microphone permission, streaming transport, turn state, barge-in, captions, transcript persistence, and playback. Provider adapter isolates vendor protocols. Wake word is opt-in with visible state.

### Orchestrator
Converts requests into structured plans, selects specialists, requests context, proposes tool calls, and reconciles results. Cannot bypass policy. Handles retries, cancellation, budgets, deadlines, and partial failure.

### Policy and approvals
Evaluates actor, workspace, project, tool, scope, target, risk, environment, and parameters. Returns allow, deny, or require approval. Approval tokens are short-lived and bound to exact action hash. Parameter changes invalidate approval.

### Memory service
Stores structured project facts, decisions, tasks, and source-linked memory. Vector retrieval supplements structured queries. Filter by user, tenant, project, sensitivity, and freshness before semantic ranking.

### Tool execution
Each tool manifest defines name/version, input/output schema, scopes, risk tier, timeout, idempotency, and verification. Tools return typed results and evidence.

### Local operator
Separate supervised process with restricted capabilities. Signed scoped job requests; isolated browser contexts; canonicalised allowlisted paths; allowlisted developer commands in isolated workspace; global stop.

### Integrations
OAuth/API adapters expose narrow actions, not unrestricted generic access. Tokens are encrypted and excluded from prompts, transcripts, screenshots, and logs.

## 4. Request lifecycle
1. User starts voice, text, or visual session.
2. Session manager authenticates and records consented input sources.
3. Context service retrieves relevant project facts, decisions, and verified activity.
4. Orchestrator creates plan, steps, tools, expected outputs, and risk classification.
5. Policy evaluates every proposed action.
6. Approval UI presents exact action, target, parameters, consequences, and expiry.
7. Router executes only permitted actions.
8. Output is validated and independently verified where possible.
9. Project/task state updates with provenance and confidence.
10. Workspace displays progress, evidence, changes, and unresolved issues.
11. Audit records actor, action, policy result, approval, tool version, timestamps, and outcome.

## 5. Specialist agents
Engineering, defensive cybersecurity, data analytics, technology research, product/design/creative, business/operations, and research/fraud analysis. Specialists share tool registry, memory, policy, evaluation, and audit. No specialist grants itself permissions.

## 6. Deployment boundaries
### Private desktop pilot
Tauri client; local FastAPI gateway/operator; encrypted local config/cache; hosted model/voice APIs via controlled credentials; optional hosted Postgres/object storage.

### Hosted multi-user evolution
Authenticated API gateway; tenant-aware orchestration/workers; managed Postgres with RLS/vector extension; encrypted object storage; queue; secrets manager; central audit pipeline; per-tenant grants and quotas.

Never expose service-role database keys, model provider keys, OAuth refresh tokens, or signing secrets to desktop renderer.

## 7. Data flow
Structured facts in relational tables. Embeddings only for approved semantic content. Media in object storage with metadata in Postgres. Raw screen/camera media transient by default. Audio retention configurable. Logs exclude secrets and minimise sensitive payloads. Derived insights store source references and timestamps.

## 8. Failure handling
Provider timeout: cancel and offer retry/fallback. Network outage: retain local task state and queue only safe idempotent work. Duplicate delivery: idempotency key. Tool failure: preserve partial results and mark incomplete. Cancellation propagates to agents, browser, voice, subprocesses. Stale memory is flagged and refreshed before consequential decisions. Migrations are versioned, reviewed, backed up, and tested.

## 9. Architecture decision records
Create ADRs for desktop shell/OS baseline, voice provider/Nigerian English benchmark, avatar/licensing, local/cloud inference, persistence/sync, operator isolation, identity/secrets, deployment region/data residency. Each ADR records context, options, evidence, decision, consequences, owner, and review date.

## 10. Quality gates
Renderer cannot invoke arbitrary OS commands; operator enforces path/process/domain/session scopes; policy is not UI-only; secrets encrypted/redacted; tenant isolation tested; approvals action-bound and replay-resistant; results verified and audited; backup, restore, revoke, and emergency-stop tested.
