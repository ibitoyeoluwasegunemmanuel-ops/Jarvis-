import os
import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

MIN_SESSION_TOKEN_LENGTH = 32

app = FastAPI(
    title="JARVIS Gateway",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)


@app.middleware("http")
async def require_local_session(request: Request, call_next):
    """Protect every route except liveness and browser CORS preflight."""
    if request.url.path == "/health" or request.method == "OPTIONS":
        return await call_next(request)

    expected = os.environ.get("JARVIS_SESSION_TOKEN", "")
    if len(expected) < MIN_SESSION_TOKEN_LENGTH:
        return JSONResponse(
            status_code=503,
            content={"detail": "gateway_session_not_configured"},
        )

    presented = request.headers.get("X-Jarvis-Session", "")
    if not presented or not secrets.compare_digest(presented, expected):
        return JSONResponse(
            status_code=401,
            content={"detail": "valid_gateway_session_required"},
        )

    return await call_next(request)


# Local development origins only. Production origins must be explicit and configured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:1420", "http://localhost:1420"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "X-Jarvis-Session"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness endpoint; does not expose secrets or internal configuration."""
    return {"status": "ok", "service": "jarvis-gateway", "version": app.version}


@app.get("/v1/system/capabilities", tags=["system"])
async def capabilities() -> dict[str, object]:
    """Report implemented gateway capabilities without implying unavailable features."""
    session_configured = (
        len(os.environ.get("JARVIS_SESSION_TOKEN", "")) >= MIN_SESSION_TOKEN_LENGTH
    )
    return {
        "service": "jarvis-gateway",
        "api_version": "v1",
        "capabilities": {
            "health_check": True,
            "authorization_policy": True,
            "gateway_session_authentication": True,
            "project_persistence": False,
            "agent_execution": False,
            "computer_use": False,
            "voice": False,
            "persistent_memory": False,
        },
        "security": {
            "default_policy": "deny_without_identity_and_scope",
            "external_side_effects_require_approval": True,
            "gateway_session_configured": session_configured,
            "owner_authentication_configured": False,
        },
    }
