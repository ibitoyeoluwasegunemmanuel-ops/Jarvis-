# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the product specifications, native desktop foundation, local gateway, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout; package manager pinned to pnpm 10.22.0.
- React/Vite desktop workspace with navigation, status cards, and gateway health polling/retries.
- FastAPI gateway with public liveness and session-protected API routes.
- Local gateway session-token gate: protected routes require a process token of at least 32 characters and use constant-time comparison.
- Tauri 2 native desktop shell with a shell-plugin permission scoped to one gateway sidecar and fixed loopback arguments only.
- Native Rust startup creates a fresh per-launch random token and passes it only to the gateway process environment; the token is not returned to JavaScript.
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
- Native authenticated request bridge from the webview to protected gateway APIs. The webview currently calls only the public liveness route; the process token remains in native/gateway processes.
- Database connection and real project/memory persistence.
- Realtime voice, avatar rendering, screen/camera sharing.
- Orchestrator, specialist execution, and actual approval issuance/consumption.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and real-machine installation/runtime validation for the Windows installer.

## Validation status
- Run #24 (43512842821): the earlier standalone Windows x64 executable built and was verified as a PE32+ GUI binary. It predates sidecar integration and is superseded by the installer build.
- Run #26 (43516816249): desktop typecheck/build passed; Ruff passed; 13 gateway tests passed.
- Run #36 (43518184999): desktop build passed, Ruff passed, and 14 gateway tests passed, including the packaged Tauri CORS preflight.
- Run #37 (43518257964): packaged gateway smoke test passed. The Windows runner started the PyInstaller binary, verified health, confirmed a missing token gets HTTP 401, and confirmed the generated session token is accepted.
- Run #38 (43518391497, commit f2883e6): all three jobs passed. This includes desktop typecheck/build, gateway lint/tests, PyInstaller sidecar build, packaged-gateway smoke test, NSIS installer build, and artifact upload.
- The Run #38 installer artifact was downloaded and verified as a Windows NSIS self-extracting PE. File: JARVIS_0.1.0_x64-setup.exe (17,968,569 bytes). It has not been installed on the owner's physical Windows machine.
- Run #40 aligns the packageManager field with the CI pnpm version; run #41 validates the reusable local sidecar build script and CI integration.
- CI still uses --no-frozen-lockfile. A generated pnpm-lock.yaml is uploaded as a CI artifact but has not yet been committed to the repository.
- An earlier sidecar-aware build (run #33, 43517957013) failed because the workflow had not yet staged the target-specific sidecar; the corrected workflow stages it before the Tauri build.

The process-level token gate is not owner authentication. The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Confirm the latest reusable sidecar build workflow (run #41) passes.
2. Commit the generated pnpm lockfile and switch CI to frozen dependency installation.
3. Add a native authenticated request bridge so the webview can call protected APIs without receiving the session token.
4. Implement owner authentication, trusted workspace membership, database access, RLS policies, and append-only audit records.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and a specialist registry using shared contracts.
7. Connect project and agent views to persistent project state.
8. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
