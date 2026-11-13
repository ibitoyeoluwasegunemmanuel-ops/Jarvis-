# JARVIS Gateway

FastAPI service for the private JARVIS desktop environment.

## Development

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
```

Set a strong local session secret before starting the gateway. Use at least 32 random characters and keep it out of source control and the frontend:

```powershell
$env:JARVIS_SESSION_TOKEN = "<a-long-random-local-secret>"
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Health endpoint: GET /health (public liveness only).

All other routes, including /v1/*, /docs, and /openapi.json, require the X-Jarvis-Session header. Missing or invalid caller tokens are rejected. If the gateway process has no token or a token shorter than 32 characters, protected routes fail closed with HTTP 503. Token comparison uses a constant-time comparison.

## Security foundation

- The gateway session token is a local process secret, not the user's permanent identity and not proof of workspace membership.
- Do not hardcode the token in the React frontend, commit it, put it in command-line arguments, or print it to logs.
- The desktop must eventually call a native, authenticated gateway bridge that adds this header without returning the secret to JavaScript.
- The native app does not yet generate or provision this token, start/monitor the gateway process, or shut it down. Until that lifecycle is implemented, this authentication gate is a tested foundation rather than a connected user experience.
- app.policy.evaluate is a fail-closed decision function; it does not execute tools.
- Read-only and reversible actions may be allowed only when identity, workspace, target, and required scope are present.
- External side effects and high-impact actions require a separate explicit approval flow.
- Cross-workspace requests are denied by default.
- Approval must be bound to the exact action and arguments, expire, and be consumed once by the eventual executor.

## Database

Apply migrations in migrations/ using a privileged migration role. The initial schema intentionally does not enable RLS until a trusted membership/identity model is implemented. Never expose these tables to anonymous clients or treat a caller-supplied workspace ID as proof of access.

## Current limitations

The gateway does not yet authenticate the owner, persist sessions, persist projects, execute tools, call model providers, implement approval consumption, or start automatically with the desktop. The local session header is an initial process-level gate only; it is not a substitute for owner authentication or a trusted authorization boundary.
