# JARVIS Cloud API

This service is separate from `services/gateway`. The desktop gateway remains
loopback-only and must never be exposed to a phone, LAN, tunnel, or public IP.

## Current slice

- Verifies Supabase Auth asymmetric access tokens against a configured JWKS URL.
- Requires issuer and `authenticated` audience validation.
- Derives user identity from the verified token subject; no caller-supplied owner ID.
- Uses a transaction-local PostgreSQL identity for RLS checks.
- Provides workspace-scoped read access to projects and monitoring alerts.
- Registers and revokes the current user's devices.
- Exposes only a non-sensitive liveness endpoint without authentication.

This is a backend foundation, not yet a complete mobile sign-in flow. Workspace
creation/onboarding, refresh-token handling, push-token delivery, alert workers,
approvals, realtime events, and production deployment are not included.

## Required configuration

- `DATABASE_URL`: PostgreSQL connection string for a dedicated `jarvis_api`
  runtime role. It must be NOBYPASSRLS and must not own the protected tables.
- `SUPABASE_JWKS_URL`: Supabase project's asymmetric JWT JWKS endpoint.
- `SUPABASE_JWT_ISSUER`: exact JWT issuer configured for that Supabase project.

Never use a Supabase service-role key or a PostgreSQL superuser as the runtime
database credential. Keep migration credentials separate from runtime credentials.
The migration assumes a privileged migration role creates the `jarvis_api` role
before applying the final grants.

## Local development

```bash
python -m venv .venv
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8787
```

Apply `migrations/0001_cloud_identity_devices.sql` with a privileged migration
role after creating the NOBYPASSRLS runtime role. Configure the three environment
variables before exercising authenticated routes.

## Security notes

- JWT verification rejects symmetric/legacy signing algorithms; configure Supabase
  Auth with an asymmetric signing key and publish its JWKS.
- The API sets `jarvis.user_id` only from the verified JWT subject.
- RLS is defense in depth, not a replacement for a least-privilege database role.
- Do not expose PostgreSQL or the local desktop gateway directly to mobile clients.
- Use HTTPS at the deployment edge, strict CORS allowlists, rate limits, request
  logging with token redaction, and secret management before public deployment.
