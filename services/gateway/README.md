# JARVIS Gateway

FastAPI service for the private JARVIS desktop environment.

## Development

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
```

Set a strong local session secret before starting the gateway manually. Use at least 32 random characters and keep it out of source control and the frontend:

```powershell
$env:JARVIS_SESSION_TOKEN = "<a-long-random-local-secret>"
uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Health endpoint: GET /health (public liveness only).

All other routes, including /v1/*, /docs, and /openapi.json, require the X-Jarvis-Session header. Missing or invalid caller tokens are rejected. If the gateway process has no token or a token shorter than 32 characters, protected routes fail closed with HTTP 503. Token comparison uses a constant-time comparison.

## Desktop integration

- The Tauri app generates a fresh token at launch and passes it to the packaged gateway sidecar through the process environment.
- The token is not returned to the webview or placed in application logs.
- The packaged gateway is restricted to loopback binding on 127.0.0.1.
- The Rust process owns the sidecar lifecycle and terminates it when the desktop exits.
- The webview currently checks only the public health endpoint. A native authenticated request bridge for protected routes is still needed.
- Windows CI builds the gateway sidecar with PyInstaller and packages it with the app; the full NSIS installer path is under validation.

## Security foundation

- The gateway session token is a local process secret, not the user's permanent identity and not proof of workspace membership.
- Do not hardcode the token in the React frontend, commit it, put it in command-line arguments, or print it to logs.
- app.policy.evaluate is a fail-closed decision function; it does not execute tools.
- Read-only and reversible actions may be allowed only when identity, workspace, target, and required scope are present.
- External side effects and high-impact actions require a separate explicit approval flow.
- Cross-workspace requests are denied by default.
- Approval must be bound to the exact action and arguments, expire, and be consumed once by the eventual executor.

## Database

Apply migrations in migrations/ using a privileged migration role. The initial schema intentionally does not enable RLS until a trusted membership/identity model is implemented. Never expose these tables to anonymous clients or treat a caller-supplied workspace ID as proof of access.

## Current limitations

The gateway does not yet authenticate the owner, persist sessions, persist projects, execute tools, call model providers, or implement approval consumption. The process token is only an initial local gate; it is not a substitute for owner authentication or a trusted authorization boundary.
