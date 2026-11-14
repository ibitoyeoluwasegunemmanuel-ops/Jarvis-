# JARVIS — Build Status

Last updated: 2026-11-14

## Repository state

JARVIS is a private, local-first Windows desktop foundation with a native Tauri shell, a loopback-only FastAPI gateway, single-owner authentication, and an owner-scoped project workspace.

### Implemented in source

- pnpm workspace with pnpm 10.22.0 and a committed lockfile.
- React/Vite desktop interface with navigation, gateway health polling/retries, owner setup/sign-in/sign-out, and Projects workspace.
- FastAPI gateway with public liveness and process-token-protected API routes.
- Gateway process token is a 32+ character random per-launch value checked with constant-time comparison.
- Local single-owner authentication. Password hashes use Argon2id; owner session tokens are stored as SHA-256 hashes with a 12-hour expiry; five invalid login attempts trigger a 60-second lockout.
- Owner data and project/task records are stored in local SQLite under the user's application-data folder (or `JARVIS_DATA_DIR` in tests/CI).
- Tauri 2 starts the packaged Python gateway sidecar with a fresh process token. The gateway binds to loopback only.
- Owner session remains in Rust-managed native state. Fixed, typed commands handle authentication, capabilities, projects, tasks, decisions, milestones, risks, and project memory; the webview cannot choose arbitrary URLs, HTTP methods, headers, shell commands, or filesystem paths.
- Native token copies are explicitly zeroized on use, logout, and runtime drop.
- Projects support owner-protected list/create/read/status operations. Statuses: `active`, `paused`, `completed`.
- Project tasks support owner-protected list/create/status operations. Statuses: `open`, `in_progress`, `done`.
- Project and task creation/status changes append immutable audit events. SQLite triggers reject updates/deletes to audit events.
- Project decisions are append-only records with title, decision, rationale, and optional source reference; each record creates an audit event.
- Project milestones support target dates, descriptions, and planned/in-progress/completed/cancelled status; creation and status changes append audit events.
- Project risk register and append-only project memory are available through owner-scoped gateway APIs and fixed typed native commands. The Projects UI loads, creates, lists and updates risks, and creates/lists source-attributed memory entries. Writes refresh the activity timeline.
- Project activity endpoint returns recent audit history; the UI displays the latest events.
- Shared TypeScript contracts exist for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covers actor, workspace, scope, target, and risk tier.
- Initial PostgreSQL migration describes future multi-user workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.

### Not implemented yet

- Trusted cloud identity/workspace membership, PostgreSQL connection, production RLS, cloud sync, or multi-user support.
- Agent orchestration, model-provider connection, specialist execution, and actual approval issuance/consumption.
- Realtime voice, Nigerian-English speech evaluation, avatar rendering, screen/camera sharing.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and installation/runtime validation on the owner's physical Windows device.

## Validation status

- GitHub Actions run #133 (run ID `43580494417`, commit `64ea11d348939b3697615af759ebc837d7b5a5bf`): desktop, gateway, and native-shell jobs all **passed**.
- Run #133 produced the `jarvis-windows-x64-installer` artifact (artifact ID `14107958293`, 19,906,991 bytes) and `jarvis-pnpm-lockfile` artifact. [View run #133 and its artifacts](https://github.com/ibitoyeoluwasegunemmanuel-ops/Jarvis-/actions/runs/43580494417).
- The successful native-shell job verifies the Windows build/package workflow in CI. It does not prove installation on the owner's physical Windows device.
- No physical Windows-device installation validation or code signing has been done.

## Security boundaries and limitations

The gateway process token is a transport gate, not owner identity. Owner accounts are single-owner and local-only. The policy module is a decision helper, not a complete tool-execution boundary. PostgreSQL RLS remains disabled until trusted workspace identity is implemented. Do not expose SQL tables to anonymous clients. No autonomous agent execution or computer use is implemented yet.

## Next integrated engineering targets

1. Implement action-bound approval issuance and single-use consumption. Bind approvals to the exact action, canonical arguments, actor/workspace/target, expiry, and nonce; reject replay or changed arguments; append audit events. Approval is not execution.
2. Add a constrained execution dispatcher that re-checks policy at execution time and only exposes explicitly allowlisted tools.
3. Build orchestrator and specialist execution behind the shared policy and approval boundary.
4. Establish trusted workspace identity and database access boundaries before cloud sync or multi-user support.
5. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
6. Validate the installer on a physical Windows device and establish code signing before broad distribution.
