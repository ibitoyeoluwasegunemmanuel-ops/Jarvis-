# JARVIS — Cross-Device and Backend Implementation Plan

Status: implementation plan for the next delivery slice
Branch: feature/cross-device-foundation

## Product decision

JARVIS is one personal AI operating environment with three clients, not three separate products:

1. Windows desktop: primary operator and local-computer integration.
2. Android and iOS: installable mobile companion for voice/chat, alerts, approvals, project status, and remote monitoring.
3. Web workspace: responsive browser access to projects, monitoring, and administration.

All clients share one authenticated owner identity, project brain, connector registry, audit history, and policy service. Device-local permissions remain device-local.

## Non-negotiable security boundary

The current Windows gateway binds to 127.0.0.1 and uses a per-launch process token. It is not a mobile-accessible server. Do not expose that loopback gateway to a LAN, public IP, tunnel, or phone.

A phone must connect only to a separately deployed HTTPS API with real owner authentication, device registration, revocation, rate limits, and workspace authorization. Do not place desktop process tokens, provider API tokens, database service-role keys, or model keys in mobile/web clients.

No background screen or camera capture. Screen/camera sharing starts only from an explicit user action with a visible indicator and stop control. Remote computer operation must remain approval-gated.

## Target architecture

- Windows: Tauri 2 + React/TypeScript; local FastAPI sidecar; SQLite local cache; Windows Credential Manager for provider secrets; local computer-use adapter with scoped permissions.
- Mobile: Flutter application for Android and iOS; secure platform storage (Android Keystore / iOS Keychain); push notifications; deep links to approval and alert details.
- Web: responsive Next.js workspace for browser access.
- Cloud API: FastAPI service over HTTPS, versioned REST endpoints and WebSocket/SSE for live status where justified.
- Identity: trusted owner identity and device sessions; short-lived access tokens, rotating refresh sessions, device revocation, recovery and step-up authentication for sensitive actions.
- Data: managed PostgreSQL with pgvector only after workspace identity is trusted; production RLS tested on every tenant-owned table. Object storage for user-approved assets only.
- Workers: Redis-backed job queue for scheduled health checks, connector polling, event processing and notification delivery. Idempotency, retries, dead-letter handling and audit records required.
- Providers: connector registry with declared read-only scopes first; secrets encrypted at rest and never returned to clients.

## API contract to establish before mobile integration

- `POST /v1/auth/device/register`
- `POST /v1/auth/session/refresh`
- `POST /v1/auth/session/revoke`
- `GET /v1/devices` and `DELETE /v1/devices/{device_id}`
- `GET /v1/workspace/overview`
- `GET /v1/projects`, `GET /v1/projects/{project_id}`
- `GET /v1/monitoring/overview`
- `GET /v1/monitoring/alerts`
- `POST /v1/monitoring/alerts/{alert_id}/acknowledge`
- `GET /v1/approvals`
- `POST /v1/approvals/{approval_id}/decision`
- `GET /v1/events/stream` for authenticated live updates

Every route must derive owner/workspace identity from the authenticated server-side session, not a client-supplied owner or workspace ID. Approval decisions must be bound to the exact action, target, arguments, expiry and requesting device.

## Mobile MVP — installable companion

### Android and iOS
- Sign in and register this phone as a named trusted device.
- Home screen: JARVIS status, recent project activity, alerts and pending approvals.
- Text chat and voice conversation with captions and push-to-talk.
- Project list, task/milestone status and source-linked activity.
- Monitoring centre for connected Vercel, Supabase and GitHub read-only status.
- Push notifications for actionable alerts and approval requests.
- Approve/reject only after displaying the exact action, target and consequences.
- Device list, revoke other sessions, sign out and emergency stop.
- Responsive layouts, accessibility labels, offline-safe cached read views and clear stale-data timestamps.

### Installation and release
- Android: debug APK for internal device testing first; signed release AAB for Google Play after privacy, permissions and device-session tests.
- iOS: simulator/device build, then TestFlight distribution; App Store release only after signing, privacy disclosures and review checks.
- Keep platform signing credentials outside source control and CI logs.
- Do not claim an installable build until a real Android/iOS build and install smoke test passes.

## Windows continuation

1. Finish the monitoring connector credential lifecycle using Windows Credential Manager or an equivalent reviewed OS-backed vault. Never ask users to paste tokens into chat or renderer fields.
2. Add scheduled read-only health checks with clear last-success timestamps, bounded retries, rate limits and an offline state.
3. Add Windows notification delivery and a notification history view.
4. Verify packaged sidecar, NSIS installer, startup/shutdown, owner session, monitoring and project workflows on a physical Windows machine.
5. Establish code signing and a safe update/rollback strategy before public distribution.
6. Keep local operator permissions scoped and visible; every consequential action requires exact approval and audit.

## Backend continuation

1. Finish current monitoring CI and correct any failing gateway, desktop or native-shell job before adding dependent features.
2. Add OS-backed encrypted provider secret storage and rotation.
3. Implement the cloud identity/device-session service separately from the local desktop gateway.
4. Establish PostgreSQL workspace ownership and production RLS; test cross-workspace denial before syncing private data.
5. Add event/job infrastructure for connector polling, deduplicated alerts and push notifications.
6. Add mobile-facing API contracts and integration tests against the same policy and audit layer.
7. Add backup/restore, session revocation, abuse limits, observability and deployment runbooks.

## Delivery order and acceptance gates

### Gate 1 — Stable Windows foundation
Latest monitoring changes have green gateway, desktop and native-shell CI. Packaged installer smoke test passes. Physical Windows installation is recorded separately.

### Gate 2 — Secure backend
Owner identity, device registration/revocation, encrypted secrets, RLS and audit tests pass. No mobile client can access the local loopback gateway.

### Gate 3 — Mobile installable alpha
Android APK installs on a physical phone; login, device revocation, alerts, projects and approvals work against the HTTPS API. iOS TestFlight build is validated on a physical iPhone.

### Gate 4 — Remote monitoring
Scheduled checks continue while the Windows desktop is closed, provided the cloud worker and provider credentials are configured. Alerts are deduplicated and delivered to registered devices. Last-success time and outages are visible.

### Gate 5 — Production release
Security review, privacy disclosures, signed artifacts, backup/restore drill, rate/cost controls, crash handling and release rollback are complete.

## Honest status reporting

Source code, CI success, an uploaded installer artifact, physical installation, and public release are separate states. Report each independently. Never say a phone app is installable until its platform build and physical-device smoke test have succeeded.
