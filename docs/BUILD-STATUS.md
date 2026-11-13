# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the baseline product specifications, desktop web workspace scaffold, gateway foundation, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout.
- React/Vite desktop workspace shell with navigation and status cards.
- FastAPI gateway with liveness and capability-reporting endpoints.
- Capability endpoint explicitly reports which major features are not implemented.
- Tauri 2 native desktop project structure with Rust entry point and Vite integration.
- Minimal `main`-window capability; no privileged filesystem, shell, microphone, camera, or capture plugins are granted.
- Desktop app launch/build scripts and runtime security notes.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering identity, workspace, scope, target, and risk tier.
- Policy unit tests covering allow, deny, and approval-required outcomes.
- Gateway endpoint tests for liveness and truthful capability reporting.
- Initial PostgreSQL migration for workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.
- GitHub Actions workflow for desktop typecheck/build and Python lint/tests.
- Environment template and ignore rules.

### Not implemented yet
- Windows installer and signed release packaging. The Tauri native shell is scaffolded but not yet compiled on Windows.
- Authentication/session security and secure IPC.
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
- Tauri 2 shell configuration and Rust project structure have been committed. A Windows GitHub Actions job has now been added to compile the native shell; its first result is pending.
- The frontend package manifest now includes Tauri dependencies. The CI install uses `--no-frozen-lockfile`; run `pnpm install` locally to refresh the committed lockfile before relying on frozen installs.
- No native Windows/Tauri compile or installer build has yet been confirmed.

The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Confirm the Windows native-shell compilation job passes.
2. Refresh and commit the pnpm lockfile for the new Tauri packages.
3. Implement a supervised local gateway lifecycle and owner-only session boundary before project writes.
4. Implement trusted workspace membership, database access, RLS policies, and append-only audit records.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and a specialist registry using shared contracts.
7. Connect workspace status to real gateway and project state.
8. Add tests for permissions, cancellation, and evidence-backed verification.
