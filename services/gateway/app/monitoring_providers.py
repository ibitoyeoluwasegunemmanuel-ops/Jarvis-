"""Read-only Vercel and Supabase account summaries.

Tokens are read from the gateway process environment and never returned or persisted.
Only fixed provider URLs are called; this module does not accept caller-supplied URLs.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

_TIMEOUT_SECONDS = 8
_MAX_RESPONSE_BYTES = 1_000_000


class ProviderUnavailable(RuntimeError):
    pass


def _get_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "JARVIS-ReadOnly-Monitor/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise ProviderUnavailable("provider_http_error")
            body = response.read(_MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ProviderUnavailable("provider_connection_failed") from error
    if len(body) > _MAX_RESPONSE_BYTES:
        raise ProviderUnavailable("provider_response_too_large")
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderUnavailable("provider_invalid_response") from error


def vercel_deployments() -> dict[str, Any]:
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    if not token:
        return {"provider": "vercel", "status": "not_configured", "deployments": []}
    try:
        payload = _get_json("https://api.vercel.com/v6/deployments?limit=10", token)
    except ProviderUnavailable as error:
        return {"provider": "vercel", "status": "unavailable", "detail": str(error), "deployments": []}
    rows = payload.get("deployments", []) if isinstance(payload, dict) else []
    deployments = []
    for item in rows[:10]:
        if not isinstance(item, dict):
            continue
        deployments.append({
            "id": str(item.get("uid", ""))[:100],
            "name": str(item.get("name", ""))[:120],
            "url": str(item.get("url", ""))[:300],
            "state": str(item.get("state", item.get("readyState", "unknown")))[:40],
            "created_at": item.get("createdAt"),
            "target": str(item.get("target", ""))[:40],
        })
    return {"provider": "vercel", "status": "connected", "deployments": deployments}


def supabase_projects() -> dict[str, Any]:
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not token:
        return {"provider": "supabase", "status": "not_configured", "projects": []}
    try:
        payload = _get_json("https://api.supabase.com/v1/projects", token)
    except ProviderUnavailable as error:
        return {"provider": "supabase", "status": "unavailable", "detail": str(error), "projects": []}
    if not isinstance(payload, list):
        return {"provider": "supabase", "status": "unavailable", "detail": "provider_invalid_response", "projects": []}
    projects = []
    for item in payload[:50]:
        if not isinstance(item, dict):
            continue
        projects.append({
            "ref": str(item.get("ref", ""))[:40],
            "name": str(item.get("name", ""))[:120],
            "region": str(item.get("region", ""))[:60],
            "status": str(item.get("status", "unknown"))[:40],
            "created_at": str(item.get("created_at", ""))[:50],
        })
    return {"provider": "supabase", "status": "connected", "projects": projects}


def provider_overview() -> dict[str, Any]:
    return {
        "read_only": True,
        "providers": [vercel_deployments(), supabase_projects()],
    }
