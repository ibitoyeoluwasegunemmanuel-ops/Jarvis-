# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the baseline product specifications, desktop web workspace scaffold, gateway foundation, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout.
- React/Vite desktop workspace shell with navigation and status cards.
- FastAPI gateway with public liveness and session-protected capability-reporting endpoints.
- Capability endpoint explicitly reports which major features are not implemented.
- Tauri 2 native desktop project structure with Rust entry point and Vite integration.
- Minimal `main`-window capability; no privileged filesystem, shell, microphone, camera, or capture plugins are granted.
- Desktop app launch/build scripts and runtime security notes.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering identity, workspace, scope, target, and risk tier.
- Policy unit tests covering allow, deny, and approval-required outcomes.
- Gateway endpoint tests for liveness, missing/invalid/unconfigured session tokens, and truthful capability reporting.
- Initial PostgreSQL migration for workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.
- GitHub Actions workflow for desktop typecheck/build, Windows native executable build/artifact, and Python lint/tests.
- Environment template and ignore rules.

### Not implemented yet
- Windows installer and signed release packaging. The native Tauri shell and standalone Windows executable are built in CI; no installer is published yet.
- Owner authentication, secure IPC, native token provisioning, and automatic gateway lifecycle. The gateway has a process-level token gate, but this is not owner authentication.
- Realtime voice, avatar rendering, screen/camera sharing.
- Database connection, trusted membership model, and production RLS policies.
- Orchestrator, specialist execution, and actual approval issuance/consumption.
- Local computer operator, browser/file tools, and integrations.
- Monitoring workers, notifications, and background scheduling.

## Validation status
- GitHub Actions run #4 (commit `c232f06`): desktop dependency installation, TypeScript typecheck, and production build passed. Gateway package installation passed; Ruff failed and pytest was skipped.
- Follow-up run #5 (commit `36ccfe2`): desktop checks passed; Ruff still failed. The workflow was updated to emit GitHub-format lint diagnostics and run pytest independently even if lint fails.
- Run #6 (`43510250466`, commit `f7075b2`): desktop typecheck/build passed; gateway pytest passed (10 tests). Ruff identified two deprecated `FrozenSet` annotations and one unsorted import block.
- Run #11 (`43510516623`, commit `0de8b65`): desktop typecheck/build passed; Ruff passed; gateway tests passed. The three lint findings are resolved.
- Tauri 2 shell configuration and Rust project structure have been committed. Windows run #23 (`43512265795`, icon commit `6273c96`) passed all three jobs, including native `cargo check` on `windows-latest`.
- The frontend package manifest now includes Tauri dependencies. The CI install uses `--no-frozen-lockfile`; run `pnpm install` locally to refresh the committed lockfile before relying on frozen installs.
- Native Windows/Tauri compilation passed in run #23 (`43512265795`).
- Run #24 (`43512842821`, commit `338b9fb`): all three jobs passed, including `cargo build --release` and upload of the Windows x64 executable artifact (`jarvis-windows-x64-executable`). The executable was retrieved and verified as a PE32+ x86-64 Windows GUI binary (8,942,592 bytes).
- The downloadable artifact is a standalone executable, not an MSI/NSIS installer. It has not been runtime-tested on the owner's Windows machine. The local gateway is not yet automatically started, so interactive agent capabilities are not available.
- Run #25 (`43516810261`) tested the new session middleware while the previous endpoint test still expected unauthenticated access; that intermediate run had 9 passed and 1 failed. Run #26 (`43516816249`) includes the updated tests and confirmed Ruff passed with 13 gateway tests passing. The desktop does not yet generate or inject the process token.

The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Refresh and commit the generated pnpm lockfile, then switch CI to frozen dependency installation.
2. Add an installer bundle and test its launch on a real Windows machine.
3. Connect native gateway lifecycle to the tested process-level session gate; generate an ephemeral secret without exposing it to the webview.
4. Implement owner authentication, trusted workspace membership, database access, RLS policies, and append-only audit records.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and a specialist registry using shared contracts.
7. Connect workspace status to real gateway and project state.
8. Add tests for permissions, cancellation, and evidence-backed verification.
