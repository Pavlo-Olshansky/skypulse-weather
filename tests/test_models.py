from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from skypulse.models import (
    CacheConfig,
    Condition,
    Forecast,
    ForecastEntry,
    Location,
    RetryConfig,
    Units,
    Weather,
    Wind,
)


def _parse_weather(data: dict[str, Any]) -> Weather:
    sys = data.get("sys", {})
    sunrise_ts = sys.get("sunrise")
    sunset_ts = sys.get("sunset")
    return Weather(
        location=Location(
            name=data["name"],
            latitude=data["coord"]["lat"],
            longitude=data["coord"]["lon"],
            country=sys.get("country", ""),
        ),
        temperature=data["main"]["temp"],
        feels_like=data["main"]["feels_like"],
        temp_min=data["main"]["temp_min"],
        temp_max=data["main"]["temp_max"],
        humidity=data["main"]["humidity"],
        pressure=data["main"]["pressure"],
        visibility=data["visibility"],
        wind=Wind(
            speed=data["wind"]["speed"],
            direction=data["wind"]["deg"],
            gust=data["wind"].get("gust"),
        ),
        clouds=data["clouds"]["all"],
        condition=Condition(
            id=data["weather"][0]["id"],
            main=data["weather"][0]["main"],
            description=data["weather"][0]["description"],
            icon=data["weather"][0]["icon"],
        ),
        observed_at=datetime.fromtimestamp(data["dt"], tz=timezone.utc),
        sunrise=datetime.fromtimestamp(sunrise_ts, tz=timezone.utc) if sunrise_ts else None,
        sunset=datetime.fromtimestamp(sunset_ts, tz=timezone.utc) if sunset_ts else None,
    )


def test_parse_current_weather(current_weather_data: dict[str, Any]) -> None:
    weather = _parse_weather(current_weather_data)

    assert weather.location.name == "London"
    assert weather.location.country == "GB"
    assert weather.temperature == 15.2
    assert weather.feels_like == 14.1
    assert weather.humidity == 72
    assert weather.pressure == 1013
    assert weather.visibility == 10000
    assert weather.wind.speed == 3.6
    assert weather.wind.direction == 220
    assert weather.wind.gust == 5.1
    assert weather.clouds == 0
    assert weather.condition.main == "Clear"
    assert weather.condition.description == "clear sky"
    assert isinstance(weather.observed_at, datetime)


def test_parse_forecast(forecast_data: dict[str, Any]) -> None:
    city = forecast_data["city"]
    loc = Location(
        name=city["name"],
        latitude=city["coord"]["lat"],
        longitude=city["coord"]["lon"],
        country=city["country"],
    )
    entries = []
    for item in forecast_data["list"]:
        entries.append(
            ForecastEntry(
                temperature=item["main"]["temp"],
                feels_like=item["main"]["feels_like"],
                temp_min=item["main"]["temp_min"],
                temp_max=item["main"]["temp_max"],
                humidity=item["main"]["humidity"],
                pressure=item["main"]["pressure"],
                visibility=item["visibility"],
                wind=Wind(
                    speed=item["wind"]["speed"],
                    direction=item["wind"]["deg"],
                    gust=item["wind"].get("gust"),
                ),
                clouds=item["clouds"]["all"],
                condition=Condition(
                    id=item["weather"][0]["id"],
                    main=item["weather"][0]["main"],
                    description=item["weather"][0]["description"],
                    icon=item["weather"][0]["icon"],
                ),
                forecast_at=datetime.fromtimestamp(item["dt"], tz=timezone.utc),
            )
        )
    forecast = Forecast(location=loc, entries=entries)

    assert forecast.location.name == "London"
    assert len(forecast.entries) == 3
    assert forecast.entries[0].temperature == 14.5
    assert forecast.entries[1].condition.main == "Rain"
    timestamps = [e.forecast_at for e in forecast.entries]
    assert timestamps == sorted(timestamps)


def test_parse_geocoding(geocoding_direct_data: list[Any]) -> None:
    locations = [
        Location(
            name=item["name"],
            latitude=item["lat"],
            longitude=item["lon"],
            country=item["country"],
            state=item.get("state"),
        )
        for item in geocoding_direct_data
    ]
    assert len(locations) == 2
    assert locations[0].name == "London"
    assert locations[0].country == "GB"
    assert locations[0].state == "England"
    assert locations[1].country == "CA"


def test_weather_sunrise_sunset(current_weather_data: dict[str, Any]) -> None:
    weather = _parse_weather(current_weather_data)
    assert weather.sunrise is not None
    assert weather.sunset is not None
    assert isinstance(weather.sunrise, datetime)
    assert isinstance(weather.sunset, datetime)
    assert weather.sunrise.tzinfo == timezone.utc
    assert weather.sunset.tzinfo == timezone.utc


def test_weather_sunrise_sunset_absent() -> None:
    weather = Weather(
        location=Location(name="X", latitude=0, longitude=0, country="XX"),
        temperature=0, feels_like=0, temp_min=0, temp_max=0,
        humidity=0, pressure=0, visibility=0,
        wind=Wind(speed=0, direction=0),
        clouds=0,
        condition=Condition(id=800, main="Clear", description="clear", icon="01d"),
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert weather.sunrise is None
    assert weather.sunset is None


def test_weather_is_frozen(current_weather_data: dict[str, Any]) -> None:
    weather = _parse_weather(current_weather_data)
    try:
        weather.temperature = 99.0  # type: ignore[misc]
        assert False, "Should have raised"
    except AttributeError:
        pass


def test_units_enum() -> None:
    assert Units.METRIC.value == "metric"
    assert Units.IMPERIAL.value == "imperial"
    assert Units.STANDARD.value == "standard"


def test_cache_config_defaults() -> None:
    cfg = CacheConfig()
    assert cfg.enabled is True
    assert cfg.ttl == 300
    assert cfg.max_entries == 128


def test_retry_config_defaults() -> None:
    cfg = RetryConfig()
    assert cfg.enabled is True
    assert cfg.max_retries == 3
    assert cfg.backoff_factor == 0.5
