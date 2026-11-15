# JARVIS — Founder Office Operations and Remote Monitoring

Status: Product specification. Dashboard connectors, monitoring workers, alert delivery and autonomous remediation are not considered implemented until each is connected, tested and demonstrated against a real system.

## Product goal

JARVIS is the owner's personal AI chief of staff and operations intelligence layer. It can connect to authorised business dashboards and operational systems, monitor defined signals while the owner is away, explain what is happening, prepare reports and alert the owner when attention is needed.

JARVIS does not replace the existing dashboards. It connects to them through approved APIs, webhooks, database views, logs and supported integrations, then provides a unified conversational and visual operations layer.

## 1. Founder Office command centre

Create a portfolio-level view covering:
- Overall status of each company/project.
- Key metrics, changes over time and last successful data refresh.
- Active incidents, failed jobs, overdue tasks and approvals awaiting the owner.
- Recent important activity and decisions.
- Upcoming deadlines, meetings, renewals and follow-ups.
- Cross-project priorities and recommended next actions.

Every metric must show its source, timestamp, definition and connection health. If a source is disconnected or stale, show "Unavailable" or "Last updated at..." rather than inventing a current value.

## 2. Initial owner workspaces

### WorldScope News
- Website availability and page/API errors.
- Article draft, review and publishing status.
- Editorial calendar and scheduled content.
- News ingestion/source pipeline health.
- Staff submissions and pending approvals.
- Traffic and advertising metrics when connected to trusted analytics/ad platforms.
- Alerts for publishing failures, broken links, stale feeds and failed scheduled jobs.

### HANDLY
- Customer and worker registration funnels.
- Verification/compliance workflow status.
- Job posts, applications, matching and completion metrics.
- Payment/escrow status only through authorised payment-provider reporting.
- API, app crash and service health.
- Support queue and unresolved incidents.

### CareLink Africa
- Parent, expert and partner waitlist counts.
- Expert verification and recruitment pipeline.
- Partnership outreach and meeting pipeline.
- Community activity and content schedule.
- Supabase/Vercel service health and failed form submissions.

### SENDLY
- Application/API health and release status.
- Payment partner connectivity and transaction reconciliation metrics through authorised provider APIs.
- Failed/pending transaction alerts and compliance workflow status.
- Never initiate transfers, refunds or changes to payment details without explicit action-bound approval and the relevant provider's controls.

### Drive Secure
- Fleet/device online status and last-seen time.
- GPS telemetry ingestion and trip processing.
- Dashcam upload and storage health.
- Geofence/incident alerts, evidence processing and fleet reports.
- Device offline, data gaps and abnormal event alerts.
- Use only customer-authorised vehicles, devices and feeds; do not imply universal camera/satellite access.

### CEO Global Founder Office
- Investor pipeline, outreach status and replies.
- Partnerships, suppliers and developer follow-ups.
- Calendar, meetings, tasks and deadlines.
- Portfolio cash-flow/reporting only from explicitly connected finance sources.
- Daily and weekly founder briefings.

## 3. Connection architecture

Each monitored system uses a registered connector with:
- Owner-selected account/workspace and declared scopes.
- Read-only access by default.
- API polling, webhooks, database views or supported log/metrics endpoints.
- Credential storage in encrypted vault/connector-managed OAuth; never in prompts, logs or source code.
- Per-source rate limits, retry/backoff, health checks and last-success timestamp.
- Schema validation, normalisation and source provenance.
- Data minimisation and project-level isolation.

Prefer vendor APIs and webhooks. Do not scrape private dashboards, bypass access controls, reuse browser cookies, or request broad database credentials when a narrow read-only role/view is sufficient.

## 4. Monitoring and alert engine

The owner defines monitored signals, thresholds, quiet hours, severity and notification channels. Examples:
- Website/API returns repeated errors.
- Worker/parent registration suddenly drops or form submissions fail.
- A device/fleet unit has not reported for its configured period.
- Scheduled news ingestion or publishing fails.
- Investor reply arrives or follow-up deadline is due.
- A deployment fails or a service's error rate crosses a threshold.

Each alert includes: what changed, affected system, evidence, first-seen time, last-seen time, severity, likely impact, suggested action and source link. Deduplicate noisy alerts and group related events into incidents. Avoid alert fatigue through thresholds, quiet hours and daily digests.

Monitoring cadence is configured per connector and constrained by provider quotas. Show "Monitoring active" only while the worker is running and its last check is fresh. If JARVIS is offline, show monitoring paused and explain missed-check windows; do not pretend it watched continuously.

## 5. Remote interaction and reports

Owner can use phone, web or desktop to:
- Ask for current status across the portfolio or a single workspace.
- Request a period report ("what changed since yesterday?").
- Open source records and supporting logs.
- Receive push/email/approved messaging notifications.
- Ask JARVIS to investigate an incident and propose remediation.
- Acknowledge, snooze, assign or escalate alerts.
- Ask for a demonstration of the dashboard or incident timeline.

Reports should distinguish facts, inferences and recommendations. Include data coverage, missing connectors and freshness.

## 6. Action and approval boundaries

Monitoring is read-only by default. JARVIS can automatically perform only pre-approved low-risk tasks within explicit rules, such as refreshing a cached report or retrying a safe idempotent read request.

Require explicit action-bound approval before:
- Sending external messages or contacting customers/investors.
- Publishing or editing public content.
- Changing production settings or deploying code.
- Issuing refunds, transfers or payments.
- Modifying customer, worker, patient/family, financial or fleet records.
- Deleting data, changing access or installing a new integration.
- Restarting production services or applying remediation with business impact.

Approval binds exact tool, account, target, arguments and expiry. Re-check policy before execution, audit all actions and verify outcomes. Provide emergency pause/disable per connector.

## 7. Alert delivery channels

Provide an in-app inbox and configurable push/email integrations. Optional WhatsApp/SMS/voice-call alerts must use an authorised provider and opt-in configuration. Messages should contain minimal sensitive information and link back to the authenticated JARVIS workspace. High-impact approval should happen in a secure authenticated interface, not solely through an unverified phone conversation.

## 8. Security and privacy

- Tenant/workspace isolation and least-privilege scopes.
- Separate secrets for each connector; encryption at rest and in transit.
- No secrets or sensitive customer data in vector memory.
- Redact sensitive fields in logs and notifications.
- Audit connector installation, reads, alert generation and actions.
- Retention, export, revocation and deletion controls.
- Health checks and token expiry/rotation alerts.
- Treat connected dashboard content as untrusted data, never as instructions to override JARVIS policy.
- For CareLink and other sensitive contexts, minimise personal and health-related data and use appropriate access controls.

## 9. Delivery order

1. Define a generic connector registry and monitoring data model.
2. Build the Founder Office UI with connection health and source freshness.
3. Connect one low-risk read-only dashboard first (recommended: Vercel deployment status + Supabase operational metrics for a selected project).
4. Add alert rules, incident timeline and mobile notifications.
5. Add WorldScope News and CareLink operational metrics.
6. Add HANDLY and Drive Secure telemetry, with appropriate data minimisation.
7. Add SENDLY reporting only through authorised payment-provider APIs and read-only scopes.
8. Add daily/weekly portfolio briefings and owner-approved remediation workflows.

## 10. Acceptance criteria

- Owner can connect/disconnect each dashboard and see exact permissions.
- JARVIS reports accurate source values with timestamps and links.
- Stale or failed connectors are clearly marked.
- Alert fires on a tested condition, is deduplicated, and reaches the selected channel.
- Owner can ask what changed during a specified time window and receive evidence.
- Monitoring pauses visibly when the worker is offline.
- No write action occurs without the correct approval.
- A complete audit trail records connector reads, alerts, approvals and actions.
