## Windows desktop cloud connection and initial project sync (Nov 15, 2026)

- Added native Tauri cloud sign-in using the same Supabase Auth email/password account as mobile.
- Added native-only cloud session storage in process memory; access/refresh tokens are zeroized on replacement, disconnect, owner logout and application exit. The session is not persisted between desktop launches yet, so the owner reconnects after restarting the app.
- Added Windows device registration/heartbeat in the cloud workspace.
- Added an idempotent first sync of local desktop project records into the shared cloud workspace, keyed by the immutable local project ID.
- Added a Projects-page cloud connection panel with explicit Connect, Sync now and Disconnect controls.
- Current sync scope is project metadata only (name, description, status). New project creation and project status changes trigger a sync while the desktop cloud session is connected; a manual Sync now action is also available. There is no periodic/background sync. Tasks, decisions, milestones, risks, memory and audit history are not yet synchronised.
- Rust/Tauri/React changes have not yet been compiled or run through CI. Do not treat this as a verified desktop release. Cloud service/database configuration is also still outstanding.

## Desktop-to-cloud project sync API (Nov 15, 2026)

- Added `POST /v1/projects/sync` to upsert desktop projects into the shared workspace using a stable local-project identifier. Repeated sync calls update the same cloud row rather than creating duplicates.
- Added a migration for the stable local ID and workspace-member write policy. Workspace viewers remain read-only; owner/admin/member roles can sync project records.
- Added authenticated device heartbeat endpoint; the mobile app sends a heartbeat when it starts and when a device is already registered.
- Added authentication-boundary tests for project sync and device heartbeat.
- This API is ready for the next native Windows integration slice, but the Windows desktop app has not yet been connected to cloud sign-in or project sync.

## Mobile authentication and workspace integration (Nov 15, 2026)

- Added Supabase Auth email/password sign-in and account creation to the Flutter app.
- Added secure access/refresh token persistence and refresh-token rotation; failed refresh clears the local session.
- Added authenticated mobile API client for workspace discovery/creation, device registration/list/revocation, workspace overview, project listing and monitoring alerts.
- The mobile dashboard now reads live API responses instead of placeholder project/alert counts. Empty states are explicit when no records exist.
- Added per-workspace device registration tracking and a device list with revoke controls.
- Updated mobile setup documentation. The app requires the deployed cloud API URL, Supabase project URL and public publishable/anon key. A service-role key must never be placed in the app.
- These are source changes only. No Supabase project or cloud database has been configured; no production cloud API is deployed. Android/iOS CI and physical-device installation have not yet been verified.
- Still outstanding: Windows desktop cloud identity/sync, push notifications, scheduled cloud monitoring workers, live updates, approvals, voice, offline sync, and production deployment hardening.

## Cross-device cloud API foundation (Nov 15, 2026)

- Added a separate `services/cloud-api` FastAPI service; it does not reuse or expose the Windows loopback gateway.
- Added Supabase Auth asymmetric JWT verification (JWKS, issuer, audience, expiry and UUID subject checks).
- Added PostgreSQL migrations for workspaces, memberships, registered devices, projects and monitoring alerts, with RLS enabled and transaction-local user identity derived only from the verified token.
- Added owner workspace bootstrap, device registration/list/revocation, workspace overview, project listing and monitoring-alert read endpoints.
- Added cloud API lint/test workflow and basic unauthenticated-route tests.
- Not yet verified by CI at this update. No cloud database, Supabase Auth project, production runtime role, hosting environment, or secrets have been configured. The service is source code only and is not deployed.
- Not yet implemented: mobile login/token refresh integration, device push tokens, notification delivery, background cloud monitoring workers, approval endpoints, live event stream, cloud sync writes, workspace invitation/membership management, backups or production observability.

## Read-only provider adapters (Nov 15, 2026)

- Added fixed-endpoint Vercel deployment and Supabase project-list adapters.
- Endpoint: `GET /v1/monitoring/providers/overview` (requires gateway process session and owner session).
- Optional local gateway environment variables: `VERCEL_TOKEN` and `SUPABASE_ACCESS_TOKEN`. Use narrowly scoped read-only tokens. The adapters read these variables at request time; they do not persist or return the token values.
- Only HTTPS GET calls to the providers' fixed API hosts are made. Responses are size-limited and reduced to selected deployment/project metadata.
- If a token is absent, the provider reports `not_configured`; connection failures are reported as unavailable. No background polling, webhooks, notification delivery, or token vault is included yet.
- Official API references: Vercel REST API https://vercel.com/docs/rest-api ; Supabase Management API https://supabase.com/docs/reference/api/introduction and list projects https://supabase.com/docs/reference/api/v1-list-all-projects.

## Monitoring foundation (Nov 15, 2026)

- Added an owner-authenticated monitoring connector registry for Vercel, Supabase, GitHub and manual sources. It records workspace, provider, declared scopes, connection state and last-check/last-success timestamps.
- The initial registry rejects write/admin scopes; no provider secrets are stored in this registry.
- Added an owner-authenticated alert inbox with severity, source reference, first/last seen times and duplicate-open-alert coalescing.
- Added API routes under `/v1/monitoring` for connector listing/registration/health metadata and alert listing/creation/acknowledgement.
- This is a metadata and alert foundation only. It does **not** yet poll Vercel/Supabase/GitHub, receive webhooks, store provider credentials, send notifications, or monitor while the desktop process is offline.
- Next: complete CI, implement encrypted connector secret storage and one actual read-only provider adapter, then schedule health checks and deliver mobile notifications.

# JARVIS — Build Status

Last updated: 2026-11-14

## Repository state

JARVIS is a private, local-first Windows desktop foundation with a native Tauri shell, a loopback-only FastAPI gateway, single-owner authentication, and an owner-scoped project workspace.

### Implemented in source

- pnpm workspace with pnpm 10.22.0 and a committed lockfile.
- React/Vite desktop interface with navigation, gateway health polling/retries, owner setup/sign-in/sign-out, and Projects workspace.
- FastAPI gateway with public liveness and process-token-protected API routes.
- Gateway process token is a 32+ character random per-launch value checked with constant-time comparison.
- Local single-owner authentication. Password hashes use Argon2id; owner session tokens are stored as SHA-256 hashes with a 12-hour expiry; five invalid login attempts trigger a 60-second lockout.
- Owner data and project/task records are stored in local SQLite under the user's application-data folder (or `JARVIS_DATA_DIR` in tests/CI).
- Tauri 2 starts the packaged Python gateway sidecar with a fresh process token. The gateway binds to loopback only.
- Owner session remains in Rust-managed native state. Fixed, typed commands handle authentication, capabilities, projects, tasks, decisions, milestones, risks, and project memory; the webview cannot choose arbitrary URLs, HTTP methods, headers, shell commands, or filesystem paths.
- Native token copies are explicitly zeroized on use, logout, and runtime drop. Approval nonces are held only in Rust-managed memory, paired with their requested TTL, and pruned/zeroized on approval creation/history access after expiry; rejection, logout, app exit, and runtime drop also clear them.
- Projects support owner-protected list/create/read/status operations. Statuses: `active`, `paused`, `completed`.
- Project tasks support owner-protected list/create/status operations. Statuses: `open`, `in_progress`, `done`.
- Project and task creation/status changes append immutable audit events. SQLite triggers reject updates/deletes to audit events.
- Project decisions are append-only records with title, decision, rationale, and optional source reference; each record creates an audit event.
- Project milestones support target dates, descriptions, and planned/in-progress/completed/cancelled status; creation and status changes append audit events.
- Project risk register and append-only project memory are available through owner-scoped gateway APIs and fixed typed native commands. The Projects UI loads, creates, lists and updates risks, and creates/lists source-attributed memory entries. Writes refresh the activity timeline.
- Project activity endpoint returns recent audit history; the UI displays the latest events.
- Shared TypeScript contracts exist for specialist tasks, risk tiers, approvals, and evidence.
- Owner-authenticated approval requests, approve/reject decisions, and project approval history are available through the gateway and desktop Projects UI. Approval nonces are retained in native Rust state and are not exposed to the webview.
- A restricted dispatcher currently allowlists only `project.task.create`. It re-checks actor scope and workspace, binds the single-use approval to the exact action/arguments/project, consumes it atomically, and rejects replay and cross-project use.
- An owner-authenticated `/v1/execution/approved` route now derives the local owner identity and `projects:write` scope on the server; callers cannot submit actor identity or scopes. It accepts only a single-use approval ID, nonce, action, and exact arguments, then invokes the restricted dispatcher. This is owner-initiated approved execution, not autonomous agent execution.
- Dispatcher execution start/success/failure events are appended to the immutable project audit log and included in the project activity timeline.
- Fail-closed policy decision module covers actor, workspace, scope, target, and risk tier.
- Initial PostgreSQL migration describes future multi-user workspaces, projects, tasks, decisions, memory, agent runs, approvals, and audit events.

### Not implemented yet

- Trusted cloud identity/workspace membership, PostgreSQL connection, production RLS, cloud sync, or multi-user support.
- The native Tauri bridge calls `/v1/execution/approved` through a fixed typed command. The approval nonce is retrieved from Rust-managed memory and is never exposed to React. The Projects UI offers an explicit Execute control for approved `project.task.create` requests, then refreshes tasks, approvals and activity. This is a narrow owner-initiated workflow, not general agent or computer execution.
- Agent orchestration, model-provider connection, trusted agent identity/scope issuance, and specialist execution. No autonomous agent execution is implemented.
- Realtime voice, Nigerian-English speech evaluation, avatar rendering, screen/camera sharing.
- Local computer operator, browser/file tools, and external integrations.
- Monitoring workers, notifications, and background scheduling.
- Code signing and installation/runtime validation on the owner's physical Windows device.

## Validation status

- GitHub Actions run #133 (run ID `43580494417`, commit `64ea11d348939b3697615af759ebc837d7b5a5bf`): desktop, gateway, and native-shell jobs all **passed**; this remains the latest fully documented installer artifact.
- Approval UI and API lifecycle were added in subsequent commits. Run #163 (commit `be3811c8b52f4a11b700a1df1ac7a4288b9900fe`) completed successfully across gateway, desktop, and native-shell. Run #164 (commit `c1a7e7fc18b1aa99accb6faaffc6c6efa8e7f794`) passed gateway and desktop; its native-shell job completed sidecar packaging and authentication smoke test and was building the Windows NSIS installer at the time of this update. Run #165 (commit `21c726a9f4f309b08fbecc45440f075e08438a2d`) adds pruning on approval-history access and explicit nonce clearing at app exit; its CI is queued. Do not treat the latest native-shell changes as verified until their CI jobs complete.
- Run #133 produced the `jarvis-windows-x64-installer` artifact (artifact ID `14107958293`, 19,906,991 bytes) and `jarvis-pnpm-lockfile` artifact. [View run #133 and its artifacts](https://github.com/ibitoyeoluwasegunemmanuel-ops/Jarvis-/actions/runs/43580494417).
- The successful native-shell job verifies the Windows build/package workflow in CI. It does not prove installation on the owner's physical Windows device.
- No physical Windows-device installation validation or code signing has been done.

## Security boundaries and limitations

The gateway process token is a transport gate, not owner identity. Owner accounts are single-owner and local-only. The policy module is a decision helper, not a complete tool-execution boundary. PostgreSQL RLS remains disabled until trusted workspace identity is implemented. Do not expose SQL tables to anonymous clients. No autonomous agent execution or computer use is implemented yet.

## Next integrated engineering targets

1. Connect the fixed native Tauri execution command to `/v1/execution/approved`, retrieving the nonce only from the Rust vault; never expose it to React. Add an explicit desktop Execute action and integration tests.
2. Bind approvals to trusted actor/workspace/target as well as exact action, canonical arguments, expiry, and nonce; reject replay or changed arguments; append audit events. Approval is not execution.
3. Build the extensible provider registry, search federation, skill lifecycle and source-linked knowledge ingestion behind the shared policy and approval boundary.\n4. Build orchestrator and specialist execution behind the shared policy and approval boundary.
5. Establish trusted workspace identity and database access boundaries before cloud sync or multi-user support.
6. Add voice, avatar, browser automation, and computer-use capabilities behind explicit permissions and tests.
7. Build mobile/web clients and shared cloud brain; then validate installers on physical devices and establish code signing before broad distribution.

## 2026-11-15 continuation — monitoring centre

### Implemented in source

- Added an owner-scoped monitoring registry for Vercel, Supabase, GitHub and manual connectors, with declared read-only scopes, connection metadata and an alert inbox. Duplicate open alerts are coalesced.
- Added fixed-endpoint, read-only Vercel deployment and Supabase project adapters. Requests use HTTPS GET only, have an 8-second timeout and a 1 MB response cap. The adapters select and bound returned fields and never return provider tokens.
- Added an owner-authenticated provider overview route and a fixed native Tauri command. Provider credentials are read from gateway process environment variables only; they are not accepted from the webview or stored in the registry.
- Added a Monitoring page with provider status, deployment/project summaries and manual refresh.

### Current limitations

- Provider checks are request-triggered when the owner opens or refreshes Monitoring. There is no background polling, webhook receiver, push notification, encrypted credential vault or monitoring while JARVIS is closed.
- Vercel and Supabase show `not_configured` until their respective environment variables are configured. Source implementation alone does not prove a live account connection.
- Do not ask the owner to paste API tokens into chat. The next credential milestone is native OS-backed secret storage (Windows Credential Manager or a reviewed equivalent), with secret values never entering React state or logs. Only after that should background scheduling be introduced.

### CI verification for this continuation

- Run #194 (run ID `43694051719`, commit `5639baf145b9aa4080144ab278e110b09799b0f4`): gateway and desktop jobs passed; native-shell was still in progress at the time of this entry. Do not describe the entire run as green until native-shell completes successfully.
- The earlier monitoring commits had failed CI due to Ruff import ordering and one TypeScript refresh-handler error; those were corrected in subsequent commits. Run #194 is the first run after the import-order correction.
