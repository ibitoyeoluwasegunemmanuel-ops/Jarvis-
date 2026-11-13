# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the baseline product specifications, desktop web workspace scaffold, gateway foundation, and first security/database foundations.

### Implemented in source
- pnpm workspace root and shared package layout.
- React/Vite desktop workspace shell with navigation and status cards.
- FastAPI gateway with liveness and capability-reporting endpoints.
- Capability endpoint explicitly reports which major features are not implemented.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering identity, workspace, scope, target, and risk tier.
- Policy unit tests covering allow, deny, and approval-required outcomes.
- Gateway endpoint tests for liveness and truthful capability reporting.
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
- GitHub Actions run #4 (commit `c232f06`): desktop dependency installation, TypeScript typecheck, and production build passed. Gateway package installation passed; Ruff failed and pytest was skipped.
- Follow-up run #5 (commit `36ccfe2`): desktop checks passed; Ruff still failed. The workflow now emits GitHub-format lint diagnostics and runs pytest independently even if lint fails. Awaiting validation of the newer commits.
- No successful end-to-end gateway test result has yet been confirmed.
- No native Windows/Tauri build has been run.

The policy module is a decision helper, not a complete security boundary. The SQL migration intentionally leaves RLS disabled until trusted workspace membership and authentication are implemented. Do not expose these tables to anonymous clients.

## Next integrated engineering targets
1. Resolve the Ruff findings and confirm gateway tests pass.
2. Establish Tauri 2 shell and secure local gateway lifecycle.
3. Add authenticated local session boundary before any project writes.
4. Implement trusted workspace membership, database access, RLS policies, and append-only audit records.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and specialist registry using shared contracts.
7. Connect workspace status to real gateway and project state.
8. Add tests for permissions, cancellation, and evidence-backed verification.
