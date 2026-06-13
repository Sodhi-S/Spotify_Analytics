from __future__ import annotations

import time
from typing import Any

import requests

from app.ingestion.rate_limiter import RateLimiter


class ApiError(RuntimeError):
    pass


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: int = 20,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    rate_limiter: RateLimiter | None = None,
) -> dict[str, Any]:
    for attempt in range(max_retries + 1):
        if rate_limiter is not None:
            rate_limiter.wait()

        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code >= 500 or response.status_code == 429:
                raise ApiError(
                    f"Retryable response {response.status_code}: {response.text[:200]}"
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ApiError("Expected a JSON object response")
            return payload
        except (requests.RequestException, ValueError, ApiError) as exc:
            if attempt >= max_retries:
                raise ApiError(str(exc)) from exc
            time.sleep(backoff_seconds * (2**attempt))

    raise ApiError("Unexpected retry loop exit")
