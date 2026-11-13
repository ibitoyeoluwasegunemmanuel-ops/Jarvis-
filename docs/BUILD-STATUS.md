# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the baseline product specifications, desktop application foundation, local gateway, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout.
- React/Vite desktop workspace with navigation, project-oriented sections, status cards, and gateway health polling with retries.
- FastAPI gateway with public liveness and session-protected API routes.
- Local gateway session-token gate: a process token of at least 32 characters is required for protected routes; token comparison is constant-time.
- Tauri 2 native desktop shell with a restricted shell-plugin scope limited to the fixed gateway sidecar and fixed loopback arguments.
- Native Rust startup generates a fresh random session token and passes it only to the gateway process environment; the token is not returned to the webview.
- Native app retains the sidecar process handle and terminates the process group when the desktop exits.
- Python sidecar entry point that refuses non-loopback binding.
- Windows CI builds the gateway sidecar with PyInstaller and is configured to package an NSIS installer.
- Gateway CORS allowlist includes development and packaged Windows Tauri webview origins.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering identity, workspace, scope, target, and risk tier.
- Gateway tests for liveness, missing/invalid/unconfigured session tokens, truthful capabilities, and packaged Tauri CORS preflight.
- Initial PostgreSQL migration for workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.
- GitHub Actions workflow for desktop typecheck/build, Windows sidecar/installer build, and Python lint/tests.
- Environment template and ignore rules.

### Not implemented yet
- A completed, verified Windows NSIS installer and signed release.
- Native authenticated request bridge from the webview to protected gateway APIs. The webview currently uses only the public liveness route; the process token remains in the native process and gateway process.
- Owner authentication, trusted workspace membership, secure identity-to-workspace binding, production RLS, and append-only audit enforcement.
- Database connection and real project/memory persistence.
- Realtime voice, avatar rendering, screen/camera sharing.
- Orchestrator, specialist execution, and actual approval issuance/consumption.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.

## Validation status
- Run #24 (43512842821): desktop build and gateway checks passed; standalone Windows x64 executable was built and verified as a PE32+ GUI binary. This older artifact predates gateway sidecar integration.
- Run #26 (43516816249): desktop typecheck/build passed; Ruff passed; 13 gateway tests passed, including the session-token boundary.
- Run #34 (43517961115): desktop and gateway jobs passed; the packaged PyInstaller gateway sidecar built successfully. The NSIS installer step is still in progress.
- Run #37 (43518257964): the desktop and gateway jobs passed; Windows sidecar packaging and authentication smoke test are in progress.
- Run #38 (43518391497): desktop and gateway jobs passed; Windows installer validation is in progress.
- An earlier sidecar-aware build (run #33, 43517957013) failed because the workflow had not yet staged the target-specific sidecar. The updated workflow now builds and places that sidecar before invoking Tauri.
- CI installs workspace dependencies with --no-frozen-lockfile. A generated lockfile artifact exists, but it has not yet been committed to the repository.

The process-level token gate is not owner authentication. The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Confirm the packaged gateway smoke test and NSIS installer build pass.
2. Commit the generated pnpm lockfile and switch CI to frozen dependency installation.
3. Add a native authenticated request bridge so the webview can call protected gateway APIs without receiving the session token.
4. Implement owner authentication, trusted workspace membership, database access, RLS policies, and append-only audit records.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and a specialist registry using shared contracts.
7. Connect project and agent views to real gateway and persistent project state.
8. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
