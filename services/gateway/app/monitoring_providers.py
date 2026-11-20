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


def _get_json(url: str, token: str = "") -> Any:
    headers = {
        "Accept": "application/vnd.github+json" if "api.github.com/" in url else "application/json",
        "User-Agent": "JARVIS-ReadOnly-Monitor/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if "api.github.com/" in url:
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(
        url,
        headers=headers,
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



def github_repository() -> dict[str, Any]:
    """Return a bounded, read-only snapshot of the configured GitHub repository."""
    repository = os.environ.get(
        "JARVIS_GITHUB_REPOSITORY",
        "ibitoyeoluwasegunemmanuel-ops/Jarvis-",
    ).strip()
    parts = repository.split("/")
    if (
        len(parts) != 2
        or any(not part or len(part) > 100 for part in parts)
        or any(not all(ch.isalnum() or ch in "-_." for ch in part) for part in parts)
    ):
        return {
            "provider": "github",
            "status": "unavailable",
            "detail": "github_repository_configuration_invalid",
            "repository": repository[:200],
            "branches": [],
            "recent_commits": [],
            "open_pull_requests": [],
        }

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    base = f"https://api.github.com/repos/{parts[0]}/{parts[1]}"
    try:
        repo_data = _get_json(base, token)
        branches_data = _get_json(base + "/branches?per_page=10", token)
        commits_data = _get_json(base + "/commits?per_page=5", token)
        pulls_data = _get_json(base + "/pulls?state=open&per_page=10", token)
    except ProviderUnavailable as error:
        return {
            "provider": "github",
            "status": "unavailable",
            "detail": str(error),
            "repository": repository,
            "branches": [],
            "recent_commits": [],
            "open_pull_requests": [],
        }

    if not isinstance(repo_data, dict) or not isinstance(branches_data, list) or not isinstance(commits_data, list) or not isinstance(pulls_data, list):
        return {
            "provider": "github",
            "status": "unavailable",
            "detail": "provider_invalid_response",
            "repository": repository,
            "branches": [],
            "recent_commits": [],
            "open_pull_requests": [],
        }

    branches = [
        {"name": str(item.get("name", ""))[:120], "protected": bool(item.get("protected", False))}
        for item in branches_data[:10] if isinstance(item, dict)
    ]
    commits = []
    for item in commits_data[:5]:
        if not isinstance(item, dict):
            continue
        commit = item.get("commit", {})
        author = commit.get("author", {}) if isinstance(commit, dict) else {}
        commits.append({
            "sha": str(item.get("sha", ""))[:12],
            "message": str(commit.get("message", "") if isinstance(commit, dict) else "")[:240],
            "author": str(author.get("name", ""))[:100] if isinstance(author, dict) else "",
            "committed_at": str(author.get("date", ""))[:40] if isinstance(author, dict) else "",
            "url": str(item.get("html_url", ""))[:300],
        })
    pulls = [
        {
            "number": item.get("number"),
            "title": str(item.get("title", ""))[:200],
            "state": str(item.get("state", "open"))[:20],
            "url": str(item.get("html_url", ""))[:300],
            "head": str(item.get("head", {}).get("ref", ""))[:120],
            "base": str(item.get("base", {}).get("ref", ""))[:120],
        }
        for item in pulls_data[:10] if isinstance(item, dict)
    ]
    return {
        "provider": "github",
        "status": "connected",
        "repository": str(repo_data.get("full_name", repository))[:200],
        "private": bool(repo_data.get("private", False)),
        "default_branch": str(repo_data.get("default_branch", ""))[:120],
        "updated_at": str(repo_data.get("updated_at", ""))[:40],
        "html_url": str(repo_data.get("html_url", ""))[:300],
        "branches": branches,
        "recent_commits": commits,
        "open_pull_requests": pulls,
    }


def provider_overview() -> dict[str, Any]:
    return {
        "read_only": True,
        "providers": [vercel_deployments(), supabase_projects(), github_repository()],
    }
