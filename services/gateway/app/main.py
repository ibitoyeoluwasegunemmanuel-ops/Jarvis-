from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="JARVIS Gateway",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)

# Local development origins only. Production origins must be explicit and configured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:1420", "http://localhost:1420"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness endpoint; does not expose secrets or internal configuration."""
    return {"status": "ok", "service": "jarvis-gateway", "version": app.version}


@app.get("/v1/system/capabilities", tags=["system"])
async def capabilities() -> dict[str, object]:
    """Report implemented gateway capabilities without implying unavailable features."""
    return {
        "service": "jarvis-gateway",
        "api_version": "v1",
        "capabilities": {
            "health_check": True,
            "authorization_policy": True,
            "project_persistence": False,
            "agent_execution": False,
            "computer_use": False,
            "voice": False,
            "persistent_memory": False,
        },
        "security": {
            "default_policy": "deny_without_identity_and_scope",
            "external_side_effects_require_approval": True,
            "production_authentication_configured": False,
        },
    }
