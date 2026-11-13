# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository now contains the baseline product specifications and the first application scaffold.

### Implemented in source
- pnpm workspace root and shared package layout.
- React/Vite desktop workspace shell with navigation and status cards.
- Local FastAPI gateway with a minimal liveness endpoint.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Desktop CI workflow for type checking and production build.
- Environment template and ignore rules.

### Not implemented yet
- Tauri native desktop runtime and Windows installer.
- Authentication/session security and secure IPC.
- Realtime voice, avatar rendering, screen/camera sharing.
- Durable project memory and database migrations.
- Orchestrator, specialist execution, policy enforcement, and approvals.
- Local computer operator, browser/file tools, and integrations.
- Monitoring workers, notifications, and background scheduling.

## Validation status
Source files have been committed to GitHub. A successful local install/build/test has not yet been run in this environment. GitHub Actions is configured to run the desktop typecheck and build when its workflow is triggered. Do not interpret a committed workflow as a passing CI result.

## Next integrated engineering targets
1. Establish Tauri 2 shell and secure local gateway lifecycle.
2. Add typed API contracts and authenticated local session boundary.
3. Implement server-side policy evaluation and append-only audit records.
4. Add PostgreSQL migrations for workspace, project, task, memory, agent, tool, approval, and audit entities.
5. Add orchestration and specialist registry using shared contracts.
6. Connect workspace status to real gateway and project state.
7. Add test suites for permissions, cancellation, and evidence-backed verification.
