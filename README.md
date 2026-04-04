# OpenWeather Python SDK

A Python SDK for the OpenWeatherMap API with sync/async support, LRU caching, and typed responses.

## Features

- **Typed responses** — all data returned as frozen dataclasses, not raw dicts
- **Sync + async** — identical API surface for both clients
- **LRU caching** — configurable TTL and max entries, thread-safe
- **Error hierarchy** — distinct exceptions for auth, rate limit, not found, timeout, network
- **Retry with backoff** — automatic retry on 5xx and 429 with exponential backoff
- **API key redaction** — keys never appear in logs, exceptions, or repr output
- **Debug logging** — named logger, silent by default

## Installation

```bash
pip install openweather-sdk
```

## Quick Start

```python
from openweather import OpenWeatherClient, Units

client = OpenWeatherClient(api_key="your-api-key", units=Units.METRIC)

weather = client.get_current_weather(city="Kyiv")
print(f"{weather.location.name}: {weather.temperature}°C, {weather.condition.description}")
print(f"Wind: {weather.wind.speed} m/s, Humidity: {weather.humidity}%")
```

## Forecast

```python
forecast = client.get_forecast(city="Berlin", count=8)  # next 24 hours

for entry in forecast.entries:
    print(f"{entry.forecast_at}: {entry.temperature}°C — {entry.condition.description}")
```

## Geocoding

```python
# City name to coordinates
locations = client.geocode("London")
for loc in locations:
    print(f"{loc.name}, {loc.country}: ({loc.latitude}, {loc.longitude})")

# Coordinates to city name
locations = client.reverse_geocode(lat=48.8566, lon=2.3522)
print(locations[0].name)  # Paris
```

## Caching

```python
from openweather import OpenWeatherClient, CacheConfig

client = OpenWeatherClient(
    api_key="your-api-key",
    cache=CacheConfig(enabled=True, ttl=600, max_entries=256),
)

# Second call returns from cache
weather1 = client.get_current_weather(city="Tokyo")
weather2 = client.get_current_weather(city="Tokyo")  # instant, from cache

# Force fresh data
weather3 = client.get_current_weather(city="Tokyo", skip_cache=True)
```

## Async Usage

```python
import asyncio
from openweather import AsyncOpenWeatherClient, Units

async def main():
    async with AsyncOpenWeatherClient(api_key="your-api-key", units=Units.METRIC) as client:
        weather = await client.get_current_weather(city="London")
        print(f"{weather.temperature}°C")

asyncio.run(main())
```

## Error Handling

```python
from openweather import OpenWeatherClient
from openweather.errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    OpenWeatherError,
)

client = OpenWeatherClient(api_key="your-api-key")

try:
    weather = client.get_current_weather(city="Atlantis")
except NotFoundError as e:
    print(f"City not found: {e.message}")
except AuthenticationError:
    print("Check your API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except OpenWeatherError as e:
    print(f"Something went wrong: {e.message}")
```

## Unit Systems

```python
from openweather import Units

# Client-level default
client = OpenWeatherClient(api_key="key", units=Units.IMPERIAL)

# Per-request override
weather = client.get_current_weather(city="NYC", units=Units.METRIC)
```

## API Coverage

| Endpoint | Method | API Version |
|----------|--------|-------------|
| Current Weather | `get_current_weather()` | v2.5 |
| 5-Day Forecast | `get_forecast()` | v2.5 |
| Direct Geocoding | `geocode()` | v1.0 |
| Reverse Geocoding | `reverse_geocode()` | v1.0 |

## Development

```bash
pip install -e ".[dev]"
pytest
mypy src/openweather
ruff check src/
```

## License

MIT
