# JARVIS — Build Status

Last updated: 2026-11-13

## Repository state
The repository contains the product specifications, native Windows desktop foundation, local gateway, single-owner authentication, and first persistent project workspace.

### Implemented in source
- pnpm workspace root and shared package layout; package manager pinned to pnpm 10.22.0.
- React/Vite desktop workspace with navigation, status cards, gateway health polling/retries, owner setup/sign-in/sign-out, and a Projects screen.
- FastAPI gateway with public liveness and session-protected API routes.
- Process-level gateway token gate: protected routes require a 32+ character random token and use constant-time comparison.
- Local single-owner setup/login/logout. Password hashes use Argon2id; owner session tokens are stored as SHA-256 hashes with a 12-hour expiry; five invalid login attempts trigger a 60-second lockout.
- Owner data stored in a local SQLite database under the user's application-data folder (or `JARVIS_DATA_DIR` in tests/CI).
- Tauri 2 native desktop shell starts the packaged Python gateway sidecar with a fresh per-launch process token.
- Native owner session remains in Rust-managed state; fixed typed commands handle setup/login/status/logout, capabilities, project list, and project create. Tokens are not returned to React.
- Native token copies are explicitly zeroized on use, logout, and runtime drop.
- Gateway supports owner-protected project list/create/read endpoints. Project ownership is determined by the gateway; callers cannot supply an owner ID.
- Project creation writes an append-only audit event; SQLite triggers reject updates/deletes of audit events.
- React Projects view loads saved projects after sign-in and supports owner-only local project creation.
- Python sidecar entrypoint refuses non-loopback binding; local Windows sidecar builder uses PyInstaller and the current Rust target triple.
- Windows CI packages the gateway sidecar, tests the session gate and owner setup/login/logout, and creates an NSIS installer.
- Shared TypeScript contracts for specialist tasks, risk tiers, approvals, and evidence.
- Fail-closed policy decision module covering actor, workspace, scope, target, and risk tier.
- Initial PostgreSQL migration for future multi-user workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.

### Not implemented yet
- Native protected project update/delete, tasks, decisions, and richer project memory APIs.
- Trusted cloud workspace membership, identity-to-workspace binding, PostgreSQL connection, production RLS, or multi-user support.
- Realtime voice, avatar rendering, screen/camera sharing.
- Orchestrator, specialist execution, model-provider connection, and actual approval issuance/consumption.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and installation/runtime validation on the owner's physical Windows device.

## Validation status
- Run #38 (`43518391497`, commit `f2883e6`): older sidecar-aware NSIS installer passed its gateway token smoke test and was uploaded. That installer predates owner sign-in and the persistent Projects UI; it is not the recommended latest build.
- Run #56 (`43521393108`): desktop typecheck/build and gateway lint/tests passed after the first owner-auth screen was added.
- Run #71 (`43522774981`, commit `672326cae6`): desktop typecheck/build passed; Ruff passed; **25 gateway tests passed**. This includes the owner-auth and project persistence tests.
- The Windows native job for run #71 is still validating the Rust project bridge and sidecar packaging.
- Run #72 (`43522883502`) adds a Windows packaged-gateway smoke test for owner setup, login, logout, and project create/list. It is queued at the time of this update.
- Earlier project-layer runs failed because four references still used the renamed `_connect` helper. Those references have now been corrected; run #71 confirms the gateway suite passes.
- CI still installs with `--no-frozen-lockfile`. A generated pnpm lockfile is available as an artifact but is not committed to the repository.

The gateway process token is a transport gate, not owner identity. Owner accounts are currently single-owner and local-only. The policy module is a decision helper, not a complete tool-execution boundary. PostgreSQL RLS remains disabled until trusted workspace identity is implemented. Do not expose the SQL tables to anonymous clients.

## Next integrated engineering targets
1. Confirm the Windows Rust build, packaged owner/project smoke test, and NSIS installer.
2. Commit the generated pnpm lockfile and switch CI to frozen dependency installation.
3. Add project update/status and task APIs with owner checks and audit coverage.
4. Add trusted workspace identity and database access boundaries before any cloud sync or multi-user support.
5. Implement approval issuance and single-use consumption bound to exact action arguments.
6. Add orchestration and specialist execution behind the shared policy engine.
7. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
