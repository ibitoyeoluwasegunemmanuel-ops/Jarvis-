import os
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.owner_auth import (
    InvalidOwnerCredentials,
    OwnerAlreadyConfigured,
    OwnerLoginRateLimited,
    OwnerNotConfigured,
    login_owner,
    owner_is_configured,
    owner_session_is_valid,
    revoke_owner_session,
    setup_owner,
)

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
    allow_origins=[
        "http://127.0.0.1:1420",
        "http://localhost:1420",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "X-Jarvis-Session"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness endpoint; does not expose secrets or internal configuration."""
    return {"status": "ok", "service": "jarvis-gateway", "version": app.version}


@app.get("/v1/system/capabilities", tags=["system"])
async def capabilities(request: Request) -> dict[str, object]:
    """Report implemented gateway capabilities without implying unavailable features."""
    session_configured = (
        len(os.environ.get("JARVIS_SESSION_TOKEN", "")) >= MIN_SESSION_TOKEN_LENGTH
    )
    owner_session = request.headers.get("X-Jarvis-Owner-Session")
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
            "owner_authentication_configured": owner_is_configured(),
            "owner_session_authenticated": owner_session_is_valid(owner_session),
        },
    }

class OwnerPasswordRequest(BaseModel):
    password: str = Field(min_length=12, max_length=256)


@app.get("/v1/auth/status", tags=["authentication"])
def owner_auth_status(request: Request) -> dict[str, bool]:
    """Return setup and session state without exposing credential material."""
    token = request.headers.get("X-Jarvis-Owner-Session")
    configured = owner_is_configured()
    authenticated = owner_session_is_valid(token)
    return {
        "owner_configured": configured,
        "setup_required": not configured,
        "authenticated": authenticated,
    }


@app.post("/v1/auth/setup", tags=["authentication"])
def owner_auth_setup(payload: OwnerPasswordRequest) -> dict[str, str]:
    """Create the single local owner account on first run."""
    try:
        token = setup_owner(payload.password)
    except OwnerAlreadyConfigured as error:
        raise HTTPException(status_code=409, detail="owner_already_configured") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"owner_session_token": token, "display_name": "Owner"}


@app.post("/v1/auth/login", tags=["authentication"])
def owner_auth_login(payload: OwnerPasswordRequest) -> dict[str, str]:
    """Authenticate the local owner and issue a short-lived native session."""
    try:
        token = login_owner(payload.password)
    except OwnerNotConfigured as error:
        raise HTTPException(status_code=409, detail="owner_setup_required") from error
    except InvalidOwnerCredentials as error:
        raise HTTPException(status_code=401, detail="invalid_owner_credentials") from error
    except OwnerLoginRateLimited as error:
        raise HTTPException(status_code=429, detail="owner_login_temporarily_locked") from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"owner_session_token": token, "display_name": "Owner"}


@app.post("/v1/auth/logout", tags=["authentication"])
def owner_auth_logout(request: Request) -> dict[str, bool]:
    """Revoke the current native owner session."""
    token = request.headers.get("X-Jarvis-Owner-Session")
    if not token or not revoke_owner_session(token):
        raise HTTPException(status_code=401, detail="owner_session_invalid")
    return {"revoked": True}

