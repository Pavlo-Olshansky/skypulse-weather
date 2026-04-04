from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from openweather._logging import get_logger
from openweather.errors import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    ServerError,
    TimeoutError,
)
from openweather.models.common import RetryConfig

_RETRYABLE_STATUS = {429, 500, 502, 503}


def _safe_params(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if k != "appid"}


def _calculate_wait(
    status_code: int, attempt: int, backoff_factor: float, headers: httpx.Headers | None
) -> float:
    if status_code == 429 and headers and "Retry-After" in headers:
        try:
            return float(int(headers["Retry-After"]))
        except (ValueError, TypeError):
            pass
        return 60.0
    if status_code == 429:
        return 60.0
    return backoff_factor * (2**attempt)


def _map_error(
    status_code: int,
    body: dict[str, Any] | str,
    *,
    endpoint: str,
    params: dict[str, Any] | None,
    api_key: str | None,
    headers: httpx.Headers | None = None,
) -> None:
    message = body.get("message", str(body)) if isinstance(body, dict) else str(body)
    common = dict(
        message=message, status_code=status_code, endpoint=endpoint,
        params=params, api_key=api_key,
    )
    if status_code == 401:
        raise AuthenticationError(**common)
    if status_code == 404:
        raise NotFoundError(**common)
    if status_code == 429:
        retry_after = 60
        if headers and "Retry-After" in headers:
            try:
                retry_after = int(headers["Retry-After"])
            except (ValueError, TypeError):
                pass
        raise RateLimitError(retry_after=retry_after, **common)
    if status_code >= 500:
        raise ServerError(**common)
    from openweather.errors import APIError
    raise APIError(**common)


def _should_retry(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUS


def _handle_response(response: httpx.Response, url: str, sp: dict[str, Any], api_key: str | None) -> Any:
    if response.status_code == 200:
        try:
            return response.json()
        except Exception:
            raise ParseError(
                raw_body=response.text, message="Failed to parse response JSON",
                endpoint=url, params=sp, api_key=api_key,
            )
    return None


def _raise_on_error(response: httpx.Response, url: str, sp: dict[str, Any], api_key: str | None) -> None:
    try:
        body: dict[str, Any] | str = response.json()
    except Exception:
        body = response.text
    _map_error(response.status_code, body, endpoint=url, params=sp, api_key=api_key, headers=response.headers)


def request_sync(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    *,
    api_key: str | None = None,
    retry: RetryConfig | None = None,
    logger: logging.Logger | None = None,
) -> Any:
    log = logger or get_logger()
    retry_cfg = retry or RetryConfig(enabled=False)
    sp = _safe_params(params)
    max_attempts = (retry_cfg.max_retries + 1) if retry_cfg.enabled else 1

    for attempt in range(max_attempts):
        try:
            log.debug("Request %s params=%s attempt=%d", url, sp, attempt + 1)
            response = client.get(url, params=params)
            log.debug("Response status=%d", response.status_code)

            result = _handle_response(response, url, sp, api_key)
            if result is not None:
                return result

            if _should_retry(response.status_code) and attempt < max_attempts - 1:
                wait = _calculate_wait(response.status_code, attempt, retry_cfg.backoff_factor, response.headers)
                log.debug("Retrying in %.1fs (status=%d)", wait, response.status_code)
                time.sleep(wait)
                continue

            _raise_on_error(response, url, sp, api_key)
        except httpx.ConnectError as exc:
            if attempt < max_attempts - 1:
                time.sleep(retry_cfg.backoff_factor * (2**attempt))
                continue
            raise NetworkError(message=str(exc), endpoint=url, params=sp, api_key=api_key) from exc
        except httpx.TimeoutException as exc:
            if attempt < max_attempts - 1:
                time.sleep(retry_cfg.backoff_factor * (2**attempt))
                continue
            raise TimeoutError(
                timeout=client.timeout.connect or 30.0,
                message=str(exc), endpoint=url, params=sp, api_key=api_key,
            ) from exc

    raise ServerError(message="Max retries exceeded", endpoint=url, params=sp, api_key=api_key)


async def request_async(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    *,
    api_key: str | None = None,
    retry: RetryConfig | None = None,
    logger: logging.Logger | None = None,
) -> Any:
    import asyncio

    log = logger or get_logger()
    retry_cfg = retry or RetryConfig(enabled=False)
    sp = _safe_params(params)
    max_attempts = (retry_cfg.max_retries + 1) if retry_cfg.enabled else 1

    for attempt in range(max_attempts):
        try:
            log.debug("Request %s params=%s attempt=%d", url, sp, attempt + 1)
            response = await client.get(url, params=params)
            log.debug("Response status=%d", response.status_code)

            result = _handle_response(response, url, sp, api_key)
            if result is not None:
                return result

            if _should_retry(response.status_code) and attempt < max_attempts - 1:
                wait = _calculate_wait(response.status_code, attempt, retry_cfg.backoff_factor, response.headers)
                log.debug("Retrying in %.1fs (status=%d)", wait, response.status_code)
                await asyncio.sleep(wait)
                continue

            _raise_on_error(response, url, sp, api_key)
        except httpx.ConnectError as exc:
            if attempt < max_attempts - 1:
                await asyncio.sleep(retry_cfg.backoff_factor * (2**attempt))
                continue
            raise NetworkError(message=str(exc), endpoint=url, params=sp, api_key=api_key) from exc
        except httpx.TimeoutException as exc:
            if attempt < max_attempts - 1:
                await asyncio.sleep(retry_cfg.backoff_factor * (2**attempt))
                continue
            raise TimeoutError(
                timeout=client.timeout.connect or 30.0,
                message=str(exc), endpoint=url, params=sp, api_key=api_key,
            ) from exc

    raise ServerError(message="Max retries exceeded", endpoint=url, params=sp, api_key=api_key)
