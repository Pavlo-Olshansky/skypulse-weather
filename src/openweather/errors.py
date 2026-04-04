from __future__ import annotations

from typing import Any


def _redact_key(value: str, api_key: str | None) -> str:
    if api_key and api_key in value:
        return value.replace(api_key, "***")
    return value


def _redact_params(params: dict[str, Any] | None, api_key: str | None) -> dict[str, Any] | None:
    if params is None or api_key is None:
        return params
    return {k: "***" if v == api_key else v for k, v in params.items()}


class OpenWeatherError(Exception):
    """Base exception for all OpenWeather client errors.

    API keys are automatically redacted from messages and representations.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        endpoint: str | None = None,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code, if applicable.
            endpoint: The API endpoint that was called.
            params: Query parameters sent with the request (keys are redacted).
            api_key: API key used for redaction (never stored in plain text).
        """
        self.message = _redact_key(message, api_key)
        self.status_code = status_code
        self.endpoint = endpoint
        self.params = _redact_params(params, api_key)
        self._api_key = api_key
        super().__init__(self.message)

    def __str__(self) -> str:
        return _redact_key(super().__str__(), self._api_key)

    def __repr__(self) -> str:
        return _redact_key(super().__repr__(), self._api_key)


class APIError(OpenWeatherError):
    """Non-2xx response from the OpenWeather API."""


class AuthenticationError(APIError):
    """401 - Invalid or missing API key."""


class NotFoundError(APIError):
    """404 - Requested resource (city, location) not found."""


class RateLimitError(APIError):
    """429 - Rate limit exceeded.

    Attributes:
        retry_after: Seconds to wait before retrying.
    """

    def __init__(self, retry_after: int = 0, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.retry_after = retry_after


class ServerError(APIError):
    """5xx - OpenWeather server error."""


class NetworkError(OpenWeatherError):
    """Connection failed - DNS, TCP, TLS errors."""


class TimeoutError(OpenWeatherError):
    """Request exceeded configured timeout.

    Attributes:
        timeout: The timeout value in seconds that was exceeded.
    """

    def __init__(self, timeout: float = 0.0, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.timeout = timeout


class ParseError(OpenWeatherError):
    """Response body could not be parsed as expected."""

    def __init__(self, raw_body: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.raw_body = raw_body[:500]
