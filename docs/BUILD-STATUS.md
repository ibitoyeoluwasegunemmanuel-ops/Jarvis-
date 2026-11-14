# JARVIS — Build Status

Last updated: 2026-11-14

## Repository state

JARVIS is a private, local-first Windows desktop foundation with a native Tauri shell, a loopback-only FastAPI gateway, single-owner authentication, and an owner-scoped project workspace.

### Implemented in source

- pnpm workspace root and shared package layout; package manager pinned to pnpm 10.22.0.
- React/Vite desktop interface with navigation, gateway health polling/retries, owner setup/sign-in/sign-out, Projects workspace, and local project/task management.
- FastAPI gateway with public liveness and process-token-protected API routes.
- Gateway process token is a 32+ character random per-launch value checked with constant-time comparison.
- Local single-owner setup/login/logout. Password hashes use Argon2id; owner session tokens are stored as SHA-256 hashes with a 12-hour expiry; five invalid login attempts trigger a 60-second lockout.
- Owner data and project/task records are stored in local SQLite under the user's application-data folder (or `JARVIS_DATA_DIR` in tests/CI).
- Tauri 2 starts the packaged Python gateway sidecar with a fresh process token. The gateway binds to loopback only.
- Owner session remains in Rust-managed native state. Fixed, typed commands handle authentication, capabilities, project list/create/status, and project task list/create/status; the webview cannot choose arbitrary URLs, HTTP methods, headers, shell commands, or filesystem paths.
- Native token copies are explicitly zeroized on use, logout, and runtime drop.
- Projects support owner-protected list/create/read/status operations. Project status values are `active`, `paused`, and `completed`.
- Project tasks support owner-protected list/create/status operations. Task status values are `open`, `in_progress`, and `done`.
- Project and task creation/status changes append immutable audit events. SQLite triggers reject updates/deletes to audit events.
- Project decisions are stored as append-only records with title, decision, rationale, and an optional source reference; each record creates an audit event.
- Project milestones support target dates, descriptions, and planned/in-progress/completed/cancelled status; creation and status changes append audit events.\n- Gateway project-brain APIs now include an owner-scoped risk register (severity, mitigation, status) and append-only project memory (category, content, source reference, confidence); writes append audit events and appear in project activity. These APIs are not yet connected to the desktop UI/native bridge.
- Owner-protected project activity endpoint returns recent audit history for projects, tasks, decisions, and milestones; the UI displays the latest events.
- React Projects view supports project creation, status changes, task creation, task listing, task status changes, milestone planning/status changes, an audit-history timeline, and a decision journal.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering actor, workspace, scope, target, and risk tier.
- Initial PostgreSQL migration describes future multi-user workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.

### Not implemented yet

- Desktop UI/native bridge for the newly added project risk register and project memory APIs.
- Trusted cloud identity/workspace membership, PostgreSQL connection, production RLS, cloud sync, or multi-user support.
- Agent orchestration, model-provider connection, specialist execution, and actual approval issuance/consumption.
- Realtime voice, Nigerian-English speech evaluation, avatar rendering, screen/camera sharing.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and installation/runtime validation on the owner's physical Windows device.

## Validation status

- Latest fully successful Windows packaging run: #100, run ID `43578241448`, commit `cfa3ee8b22`.
- Desktop typecheck/build: passed.
- Gateway Ruff lint: passed.
- Gateway tests on run #100: **33 passed**, with one Starlette/httpx deprecation warning.
- Windows native-shell job on run #100: passed Rust/native build, packaged-gateway health/authentication, owner setup/login/logout, project create/list/status, project-task create/list/status, project activity history smoke test, NSIS installer build, and artifact upload.
- Verified Windows installer artifact: `jarvis-windows-x64-installer` (artifact ID `14107218567`, approximately 19.8 MB). [Open the successful run and download its artifact](https://github.com/ibitoyeoluwasegunemmanuel-ops/Jarvis-/actions/runs/43578241448).
- Run #123 validates project milestones plus the decision journal: Ruff passed, **37 gateway tests passed**, and desktop typecheck/build passed. Windows native-shell packaging and the expanded milestone smoke test are still running.
- No physical Windows-device installation validation or code signing has been done.

## Security boundaries and limitations

The gateway process token is a transport gate, not owner identity. Owner accounts are single-owner and local-only. The policy module is a decision helper, not a complete tool-execution boundary. PostgreSQL RLS remains disabled until trusted workspace identity is implemented. Do not expose the SQL tables to anonymous clients. No autonomous agent execution or computer use is implemented yet.

## Next integrated engineering targets

1. Complete Windows native-shell validation, packaged gateway smoke tests for task operations, and NSIS artifact verification.
2. Connect the new project risk register and append-only project memory APIs to typed native commands and the desktop workspace.
3. Establish trusted workspace identity and database access boundaries before cloud sync or multi-user support.
4. Implement approval issuance and single-use consumption bound to exact action arguments.
5. Add orchestrator and specialist execution behind the shared policy engine.
6. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
7. Commit a generated pnpm lockfile and use frozen dependency installation in CI.
