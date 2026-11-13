# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the product specifications, native desktop foundation, local gateway, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout; package manager pinned to pnpm 10.22.0.
- React/Vite desktop workspace with navigation, status cards, gateway health polling/retries, and a live gateway session-status indicator.
- FastAPI gateway with public liveness and session-protected API routes.
- Local gateway session-token gate: protected routes require a process token of at least 32 characters and use constant-time comparison.
- Tauri 2 native desktop shell with a shell-plugin permission scoped to one gateway sidecar and fixed loopback arguments only.
- Native Rust startup creates a fresh per-launch random token and passes it only to the gateway process environment; the token is not returned to JavaScript.
- Native Rust exposes one typed `get_gateway_capabilities` command. It calls one fixed read-only loopback route, applies the token header natively, uses a five-second timeout, and returns only the JSON response.
- The React workspace invokes that native command to display the actual gateway session status; the webview never handles the session token.
- Native app retains the sidecar process handle and terminates the process group when JARVIS exits.
- Packaged gateway entry point that refuses non-loopback binding.
- PowerShell build helper for local Windows sidecar creation using PyInstaller and the detected Rust target triple.
- Windows CI builds the gateway sidecar with PyInstaller, smoke-tests token enforcement, and packages an NSIS installer.
- Gateway CORS allowlist includes development and packaged Windows Tauri webview origins.
- Gateway tests cover liveness, missing/invalid/unconfigured session tokens, capability truthfulness, and Tauri CORS preflight.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering identity, workspace, scope, target, and risk tier.
- Initial PostgreSQL migration for workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.

### Not implemented yet
- Owner authentication, trusted workspace membership, identity-to-workspace binding, production RLS, and enforced append-only audit records.
- Authenticated write bridge, project/task CRUD, and persistent project/memory storage.
- Realtime voice, avatar rendering, screen/camera sharing.
- Orchestrator, specialist execution, and actual approval issuance/consumption.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and real-machine installation/runtime validation for the Windows installer.

## Validation status
- Run #24 (43512842821): earlier standalone Windows x64 executable built and verified; predates sidecar integration and is superseded.
- Run #26 (43516816249): desktop typecheck/build passed; Ruff passed; 13 gateway tests passed.
- Run #36 (43518184999): desktop build passed, Ruff passed, and 14 gateway tests passed, including packaged Tauri CORS preflight.
- Run #37 (43518257964): packaged gateway smoke test passed; missing token produced HTTP 401 and valid process token was accepted.
- Run #38 (43518391497, commit f2883e6): all jobs passed, including desktop build, gateway lint/tests, PyInstaller sidecar, authentication smoke test, NSIS installer, and artifact upload.
- The Run #38 installer artifact was downloaded and verified as a Windows NSIS self-extracting PE: `JARVIS_0.1.0_x64-setup.exe`, 17,968,569 bytes. It has not been installed on a physical Windows device.
- Run #41 (43519153309): desktop and gateway jobs passed; sidecar build and smoke test passed; installer packaging was in progress at last check.
- Runs #42–#44 are validating the new native capability bridge and UI. Desktop typecheck/build and Python gateway tests have passed in these runs; Windows native packaging is in progress.
- CI still uses `--no-frozen-lockfile`. A generated pnpm lockfile is available as an artifact but has not yet been committed.

The process-level token gate is not owner authentication. The native bridge is read-only and narrowly scoped. The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Confirm Windows native bridge compile and installer build.
2. Commit the generated pnpm lockfile and switch CI to frozen dependency installation.
3. Implement owner authentication and trusted workspace membership before any project writes.
4. Add typed, approval-gated project/task operations and persistent local project state.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and a specialist registry using shared contracts.
7. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
