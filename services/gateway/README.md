# JARVIS Gateway

FastAPI service for the private JARVIS desktop environment.

## Development

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Health endpoint: `GET /health`.

## Security foundation

- `app.policy.evaluate` is a fail-closed decision function; it does not execute tools.
- Read-only and reversible actions may be allowed only when identity, workspace, target, and required scope are present.
- External side effects and high-impact actions require a separate explicit approval flow.
- Cross-workspace requests are denied by default.
- Approval must be bound to the exact action and arguments, expire, and be consumed once by the eventual executor.

## Database

Apply migrations in `migrations/` using a privileged migration role. The initial schema intentionally does not enable RLS until a trusted membership/identity model is implemented. Never expose these tables to anonymous clients or treat a caller-supplied workspace ID as proof of access.

## Current limitations

The gateway does not yet authenticate users, persist sessions, execute tools, call model providers, or implement approval consumption. The policy module is an early guardrail, not a complete security boundary.
