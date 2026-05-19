"""Shared utilities for all pipeline ingest scripts."""

from __future__ import annotations

import time

import requests
from pybaseball.datasources.bref import BRefSession

from stats.models import IngestionLog

TRANSIENT_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
)


def fetch_with_retry(
    session: BRefSession,
    url: str,
    retries: int = 3,
    backoff: int = 20,
) -> requests.Response:
    """Fetch a URL via BRefSession, retrying on transient network errors."""
    for attempt in range(1, retries + 1):
        try:
            return session.get(url)
        except TRANSIENT_ERRORS as exc:
            if attempt == retries:
                raise
            wait = backoff * attempt
            print(f"    network error ({exc}), retrying in {wait}s ({attempt}/{retries})")
            time.sleep(wait)
    raise RuntimeError("fetch_with_retry: exhausted retries")


def already_ingested(source_key: str) -> bool:
    return IngestionLog.objects.filter(source=source_key, status="success").exists()


def log_success(source_key: str, rows: int) -> None:
    IngestionLog.objects.create(source=source_key, rows_loaded=rows, status="success")


def log_error(source_key: str, exc: Exception) -> None:
    IngestionLog.objects.create(
        source=source_key, rows_loaded=0, status="error", error_msg=str(exc)
    )
