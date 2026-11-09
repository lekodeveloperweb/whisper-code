"""Shared Bearer-token header builder for OpenAI-compatible endpoints."""

from __future__ import annotations


def auth_headers(api_key: str | None) -> dict[str, str]:
    """Return request headers for an OpenAI-compatible endpoint.

    >>> auth_headers("sk-abc")
    {'Authorization': 'Bearer sk-abc'}
    >>> auth_headers(None)
    {}
    """
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}
