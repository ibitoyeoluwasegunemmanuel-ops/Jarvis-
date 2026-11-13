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
