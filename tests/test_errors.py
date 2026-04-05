from __future__ import annotations

from openweather._errors import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    OpenWeatherError,
    ParseError,
    RateLimitError,
    ServerError,
    TimeoutError,
)

API_KEY = "secret-key-12345"


def test_error_hierarchy() -> None:
    assert issubclass(APIError, OpenWeatherError)
    assert issubclass(AuthenticationError, APIError)
    assert issubclass(NotFoundError, APIError)
    assert issubclass(RateLimitError, APIError)
    assert issubclass(ServerError, APIError)
    assert issubclass(NetworkError, OpenWeatherError)
    assert issubclass(TimeoutError, OpenWeatherError)
    assert issubclass(ParseError, OpenWeatherError)


def test_api_key_redacted_in_message() -> None:
    err = OpenWeatherError(
        message=f"Invalid API key: {API_KEY}",
        api_key=API_KEY,
    )
    assert API_KEY not in err.message
    assert "***" in err.message


def test_api_key_redacted_in_str() -> None:
    err = OpenWeatherError(
        message=f"Error with key {API_KEY}",
        api_key=API_KEY,
    )
    assert API_KEY not in str(err)
    assert "***" in str(err)


def test_api_key_redacted_in_repr() -> None:
    err = OpenWeatherError(
        message=f"Error with key {API_KEY}",
        api_key=API_KEY,
    )
    assert API_KEY not in repr(err)


def test_api_key_redacted_in_params() -> None:
    err = OpenWeatherError(
        message="test",
        params={"appid": API_KEY, "q": "London"},
        api_key=API_KEY,
    )
    assert err.params is not None
    assert err.params["appid"] == "***"
    assert err.params["q"] == "London"


def test_rate_limit_error_retry_after() -> None:
    err = RateLimitError(
        retry_after=30,
        message="Rate limited",
        status_code=429,
    )
    assert err.retry_after == 30
    assert err.status_code == 429
    assert isinstance(err, APIError)


def test_timeout_error_timeout_value() -> None:
    err = TimeoutError(
        timeout=15.0,
        message="Request timed out",
    )
    assert err.timeout == 15.0


def test_parse_error_raw_body() -> None:
    err = ParseError(
        raw_body="<html>Server Error</html>",
        message="Failed to parse",
    )
    assert err.raw_body == "<html>Server Error</html>"


def test_parse_error_truncates_raw_body() -> None:
    long_body = "x" * 1000
    err = ParseError(raw_body=long_body, message="Failed to parse")
    assert len(err.raw_body) == 500


def test_error_carries_context() -> None:
    err = ServerError(
        message="Internal server error",
        status_code=500,
        endpoint="https://api.openweathermap.org/data/2.5/weather",
        params={"q": "London"},
    )
    assert err.status_code == 500
    assert err.endpoint == "https://api.openweathermap.org/data/2.5/weather"
    assert err.params == {"q": "London"}
