"""Shared Redis client for cross-invocation state (sessions, batch jobs).

REDIS_URL is optional; when unset, app.session and batch.store fall back to
in-process dicts — correct for a single long-lived instance (Docker Compose,
local dev, tests) but required on Vercel, where each request may hit a
different serverless instance.
"""

from __future__ import annotations

import os

import redis

_REDIS_URL = os.getenv("REDIS_URL")

client: redis.Redis | None = redis.Redis.from_url(_REDIS_URL, decode_responses=True) if _REDIS_URL else None


def delete_by_prefix(prefix: str) -> None:
    """Test helper — delete all keys starting with `prefix`."""
    if client is None:
        return
    for key in client.scan_iter(f"{prefix}*"):
        client.delete(key)
