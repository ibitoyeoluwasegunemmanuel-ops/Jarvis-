# JARVIS Cloud API

This service is separate from `services/gateway`. The desktop gateway remains
loopback-only and must never be exposed to a phone, LAN, tunnel, or public IP.

## Current slice

- Verifies Supabase Auth asymmetric access tokens against a configured JWKS URL.
- Requires issuer and `authenticated` audience validation.
- Derives user identity from the verified token subject; no caller-supplied owner ID.
- Uses a transaction-local PostgreSQL identity for RLS checks. Tenant policies use direct membership predicates; the migrations avoid SECURITY DEFINER helpers.
- Supports owner workspace bootstrap, device registration/list/revocation, and authenticated device heartbeat timestamps.
- Provides workspace-scoped project and alert reads, plus idempotent desktop project sync keyed by local project ID.
- Stores workspace-scoped memory entries (preferences, facts, decisions, notes and references) for authenticated cross-device retrieval; writes are limited to workspace owners, admins and members.
- Records mobile device heartbeats and supports per-user device revocation.
- Exposes only a non-sensitive liveness endpoint without authentication.

The Flutter mobile source now includes Supabase Auth email/password sign-in,
secure access/refresh token storage, workspace discovery/creation, device
registration/revocation, and read calls for workspace projects and alerts.
The service itself does not issue or store passwords or refresh tokens; Supabase
Auth owns the identity session. Workspace invitations/membership administration,
push-token delivery, alert workers, approvals, realtime events, and production
deployment are not included.

## Required configuration

- `DATABASE_URL`: PostgreSQL connection string for a dedicated `jarvis_api`
  runtime role. It must be NOBYPASSRLS and must not own the protected tables.
- `SUPABASE_JWKS_URL`: Supabase project's asymmetric JWT JWKS endpoint.
- `SUPABASE_JWT_ISSUER`: exact JWT issuer configured for that Supabase project.

Never use a Supabase service-role key or a PostgreSQL superuser as the runtime
database credential. Keep migration credentials separate from runtime credentials.

Before applying migrations, provision the runtime role using a privileged
database administrator connection (set its password through your secret manager):

```sql
CREATE ROLE jarvis_api LOGIN NOBYPASSRLS;
```

Then apply `migrations/0001_cloud_identity_devices.sql`,
`migrations/0002_workspace_bootstrap.sql`, and
`migrations/0003_project_sync.sql` in order with the migration-owner role. The
runtime role must not own the schema or protected tables. The migrations grant
only the operations needed by this first API slice.

## Local development

```bash
python -m venv .venv
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

The container image is built from this directory with `docker build -t jarvis-cloud-api .`.
Configure all three environment variables in the deployment platform's secret
manager. Terminate public traffic at HTTPS and restrict CORS to the actual app
origins when browser access is introduced.

## Security notes

- JWT verification rejects symmetric/legacy signing algorithms; configure Supabase
  Auth with an asymmetric signing key and publish its JWKS.
- The API sets `jarvis.user_id` only from the verified JWT subject.
- RLS is defense in depth, not a replacement for a least-privilege database role.
- Do not expose PostgreSQL or the local desktop gateway directly to mobile clients.
- Use HTTPS at the deployment edge, strict CORS allowlists, rate limits, request
  logging with token redaction, and secret management before public deployment.
