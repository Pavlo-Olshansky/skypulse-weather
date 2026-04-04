from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def api_key() -> str:
    return "test-api-key-12345"


def load_fixture(name: str) -> dict[str, Any] | list[Any]:
    path = FIXTURES_DIR / name
    return json.loads(path.read_text())  # type: ignore[no-any-return]


@pytest.fixture()
def current_weather_data() -> dict[str, Any]:
    return load_fixture("current_weather.json")  # type: ignore[return-value]


@pytest.fixture()
def forecast_data() -> dict[str, Any]:
    return load_fixture("forecast.json")  # type: ignore[return-value]


@pytest.fixture()
def geocoding_direct_data() -> list[Any]:
    return load_fixture("geocoding_direct.json")  # type: ignore[return-value]


@pytest.fixture()
def geocoding_reverse_data() -> list[Any]:
    return load_fixture("geocoding_reverse.json")  # type: ignore[return-value]
