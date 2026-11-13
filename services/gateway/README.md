# JARVIS Gateway

Local development API boundary. The current implementation exposes a non-sensitive liveness endpoint only; it does not yet execute tools, access files, or call model providers.

## Run locally
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Health: http://127.0.0.1:8765/health

Do not bind the local operator to 0.0.0.0. Production CORS, authentication, and IPC security require explicit configuration before exposing additional routes.
