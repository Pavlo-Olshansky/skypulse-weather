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
_NON_RETRYABLE_ERROR_STATUS = {401, 404}


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
        message=message,
        status_code=status_code,
        endpoint=endpoint,
        params=params,
        api_key=api_key,
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
    safe_params = {k: v for k, v in params.items() if k != "appid"}
    max_attempts = (retry_cfg.max_retries + 1) if retry_cfg.enabled else 1

    for attempt in range(max_attempts):
        try:
            log.debug("Request %s params=%s attempt=%d", url, safe_params, attempt + 1)
            response = client.get(url, params=params)
            log.debug("Response status=%d", response.status_code)

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    raise ParseError(
                        raw_body=response.text,
                        message="Failed to parse response JSON",
                        endpoint=url,
                        params=safe_params,
                        api_key=api_key,
                    )

            if _should_retry(response.status_code) and attempt < max_attempts - 1:
                if response.status_code == 429:
                    retry_after = 60
                    if "Retry-After" in response.headers:
                        try:
                            retry_after = int(response.headers["Retry-After"])
                        except (ValueError, TypeError):
                            pass
                    wait = retry_after
                else:
                    wait = retry_cfg.backoff_factor * (2**attempt)
                log.debug("Retrying in %.1fs (status=%d)", wait, response.status_code)
                time.sleep(wait)
                continue

            try:
                body = response.json()
            except Exception:
                body = response.text

            _map_error(
                response.status_code,
                body,
                endpoint=url,
                params=safe_params,
                api_key=api_key,
                headers=response.headers,
            )
        except httpx.ConnectError as exc:
            if attempt < max_attempts - 1:
                wait = retry_cfg.backoff_factor * (2**attempt)
                log.debug("Connection error, retrying in %.1fs: %s", wait, exc)
                time.sleep(wait)
                continue
            raise NetworkError(
                message=str(exc),
                endpoint=url,
                params=safe_params,
                api_key=api_key,
            ) from exc
        except httpx.TimeoutException as exc:
            if attempt < max_attempts - 1:
                wait = retry_cfg.backoff_factor * (2**attempt)
                log.debug("Timeout, retrying in %.1fs: %s", wait, exc)
                time.sleep(wait)
                continue
            raise TimeoutError(
                timeout=client.timeout.connect or 30.0,
                message=str(exc),
                endpoint=url,
                params=safe_params,
                api_key=api_key,
            ) from exc

    raise ServerError(
        message="Max retries exceeded",
        endpoint=url,
        params=safe_params,
        api_key=api_key,
    )


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
    safe_params = {k: v for k, v in params.items() if k != "appid"}
    max_attempts = (retry_cfg.max_retries + 1) if retry_cfg.enabled else 1

    for attempt in range(max_attempts):
        try:
            log.debug("Request %s params=%s attempt=%d", url, safe_params, attempt + 1)
            response = await client.get(url, params=params)
            log.debug("Response status=%d", response.status_code)

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    raise ParseError(
                        raw_body=response.text,
                        message="Failed to parse response JSON",
                        endpoint=url,
                        params=safe_params,
                        api_key=api_key,
                    )

            if _should_retry(response.status_code) and attempt < max_attempts - 1:
                if response.status_code == 429:
                    retry_after = 60
                    if "Retry-After" in response.headers:
                        try:
                            retry_after = int(response.headers["Retry-After"])
                        except (ValueError, TypeError):
                            pass
                    wait = retry_after
                else:
                    wait = retry_cfg.backoff_factor * (2**attempt)
                log.debug("Retrying in %.1fs (status=%d)", wait, response.status_code)
                await asyncio.sleep(wait)
                continue

            try:
                body = response.json()
            except Exception:
                body = response.text

            _map_error(
                response.status_code,
                body,
                endpoint=url,
                params=safe_params,
                api_key=api_key,
                headers=response.headers,
            )
        except httpx.ConnectError as exc:
            if attempt < max_attempts - 1:
                wait = retry_cfg.backoff_factor * (2**attempt)
                log.debug("Connection error, retrying in %.1fs: %s", wait, exc)
                await asyncio.sleep(wait)
                continue
            raise NetworkError(
                message=str(exc),
                endpoint=url,
                params=safe_params,
                api_key=api_key,
            ) from exc
        except httpx.TimeoutException as exc:
            if attempt < max_attempts - 1:
                wait = retry_cfg.backoff_factor * (2**attempt)
                log.debug("Timeout, retrying in %.1fs: %s", wait, exc)
                await asyncio.sleep(wait)
                continue
            raise TimeoutError(
                timeout=client.timeout.connect or 30.0,
                message=str(exc),
                endpoint=url,
                params=safe_params,
                api_key=api_key,
            ) from exc

    raise ServerError(
        message="Max retries exceeded",
        endpoint=url,
        params=safe_params,
        api_key=api_key,
    )
