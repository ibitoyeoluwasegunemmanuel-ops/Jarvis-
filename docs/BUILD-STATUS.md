# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the baseline product specifications, desktop web workspace scaffold, gateway foundation, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout.
- React/Vite desktop workspace shell with navigation and status cards.
- Local FastAPI gateway with a minimal liveness endpoint.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering identity, workspace, scope, target, and risk tier.
- Policy unit tests covering allow, deny, and approval-required outcomes.
- Initial PostgreSQL migration for workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.
- GitHub Actions workflow for desktop typecheck/build and Python lint/tests.
- Environment template and ignore rules.

### Not implemented yet
- Tauri native desktop runtime and Windows installer.
- Authentication/session security and secure IPC.
- Realtime voice, avatar rendering, screen/camera sharing.
- Database connection, trusted membership model, and production RLS policies.
- Orchestrator, specialist execution, and actual approval issuance/consumption.
- Local computer operator, browser/file tools, and integrations.
- Monitoring workers, notifications, and background scheduling.

## Validation status
The new CI workflow run #2 was observed in the queued state; no passing result has been confirmed. The previous desktop-only CI run failed during the pnpm/action-setup step, before dependency installation or project checks ran. Python tests have been added but have not yet been confirmed passing in CI or locally.

The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Diagnose and resolve the pnpm setup failure, then obtain a passing desktop build.
2. Establish Tauri 2 shell and secure local gateway lifecycle.
3. Add typed API contracts and authenticated local session boundary.
4. Implement trusted workspace membership, database access, RLS policies, and append-only audit records.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and specialist registry using shared contracts.
7. Connect workspace status to real gateway and project state.
8. Add tests for permissions, cancellation, and evidence-backed verification.
