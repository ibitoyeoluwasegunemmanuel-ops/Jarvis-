"""Bounded retrieval of owner-scoped project memory for conversation context."""
from __future__ import annotations

import re
from typing import Any

from app.owner_auth import connect_database
from app.project_brain import _ensure_tables

_STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "can", "could", "does",
    "for", "from", "have", "help", "into", "just", "more", "please", "that",
    "the", "their", "them", "then", "there", "this", "what", "when", "where",
    "which", "with", "would", "you", "your",
}


def _terms(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]{3,}", value.lower())
        if token not in _STOP_WORDS
    }


def retrieve_project_memory(query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Return only relevant, bounded memory snippets belonging to the local owner."""
    if not isinstance(query, str) or not query.strip():
        return []
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ValueError("memory_retrieval_limit_invalid")

    terms = _terms(query)
    connection = connect_database()
    try:
        _ensure_tables(connection)
        rows = connection.execute(
            """SELECT m.category, m.content, p.name AS project_name, m.created_at
               FROM project_memory AS m
               JOIN projects AS p ON p.id = m.project_id
               WHERE m.owner_id = 1 AND p.owner_id = 1
               ORDER BY m.created_at DESC
               LIMIT 300"""
        ).fetchall()
    finally:
        connection.close()

    ranked: list[tuple[int, float, dict[str, Any]]] = []
    for row in rows:
        item = dict(row)
        content_terms = _terms(f"{item['project_name']} {item['category']} {item['content']}")
        overlap = len(terms & content_terms)
        if not overlap:
            continue
        ranked.append((
            overlap,
            float(item["created_at"]),
            {
                "category": str(item["category"]),
                "project_name": str(item["project_name"])[:100],
                "content": str(item["content"])[:1000],
            },
        ))
    ranked.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    return [entry[2] for entry in ranked[:limit]]
