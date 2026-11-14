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
- React Projects view supports project creation, status changes, task creation, task listing, and task status changes.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering actor, workspace, scope, target, and risk tier.
- Initial PostgreSQL migration describes future multi-user workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.

### Not implemented yet

- Project milestones, decisions, risks, project memory, and richer project history APIs.
- Trusted cloud identity/workspace membership, PostgreSQL connection, production RLS, cloud sync, or multi-user support.
- Agent orchestration, model-provider connection, specialist execution, and actual approval issuance/consumption.
- Realtime voice, Nigerian-English speech evaluation, avatar rendering, screen/camera sharing.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and installation/runtime validation on the owner's physical Windows device.

## Validation status

- Latest observed CI run: #92, run ID `43577495073`, commit `5a4743ea6b`.
- Desktop typecheck/build: passed.
- Gateway Ruff lint: passed.
- Gateway tests: **32 passed**, with one Starlette/httpx deprecation warning.
- Windows native-shell job: still running at the time of this update. Do not treat the latest installer as verified or ready until the job completes and its artifact is confirmed.
- An earlier Windows native-shell run successfully compiled the Rust desktop and smoke-tested the packaged gateway with owner setup/login/logout and project create/list. That earlier smoke test predates project-task commands.

## Security boundaries and limitations

The gateway process token is a transport gate, not owner identity. Owner accounts are single-owner and local-only. The policy module is a decision helper, not a complete tool-execution boundary. PostgreSQL RLS remains disabled until trusted workspace identity is implemented. Do not expose the SQL tables to anonymous clients. No autonomous agent execution or computer use is implemented yet.

## Next integrated engineering targets

1. Complete Windows native-shell validation, packaged gateway smoke tests for task operations, and NSIS artifact verification.
2. Add project milestones, decisions, risk records, and project activity history.
3. Establish trusted workspace identity and database access boundaries before cloud sync or multi-user support.
4. Implement approval issuance and single-use consumption bound to exact action arguments.
5. Add orchestrator and specialist execution behind the shared policy engine.
6. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
7. Commit a generated pnpm lockfile and use frozen dependency installation in CI.
