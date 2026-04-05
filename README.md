# SkyPulse

Weather, space weather, and how they affect you — Python SDK with sync/async support, LRU caching, and typed responses.

## Features

- **Typed responses** — all data returned as frozen dataclasses, not raw dicts
- **Sync + async** — identical API surface for both clients
- **LRU caching** — configurable TTL and max entries, thread-safe
- **Geomagnetic storms** — real-time Kp index and 3-day forecast from NOAA SWPC
- **Health impact** — Kp-based health risk assessment with latitude adjustment
- **Storm alerts** — location-aware alerts with aurora visibility prediction
- **Auto-location** — IP-based geolocation for hands-free weather and storm queries
- **Error hierarchy** — distinct exceptions for auth, rate limit, not found, timeout, network
- **Retry with backoff** — automatic retry on 5xx and 429 with exponential backoff
- **API key redaction** — keys never appear in logs, exceptions, or repr output

## Installation

```bash
pip install skypulse
```

Requires Python 3.9+. Dependencies: `httpx`, `cachetools`.

## Quick Start

```python
from skypulse import SkyPulseClient, Units

client = SkyPulseClient(api_key="your-api-key", units=Units.METRIC)

weather = client.get_current_weather(city="Kyiv")
print(f"{weather.location.name}: {weather.temperature}°C, {weather.condition.description}")
# "Kyiv: 18.5°C, scattered clouds"
print(f"Wind: {weather.wind.speed} m/s, Humidity: {weather.humidity}%")
# "Wind: 3.6 m/s, Humidity: 72%"
```

The API key can also be set via the `SKYPULSE_API_KEY` or `OPENWEATHER_API_KEY` environment variable.

## Weather

### Current Weather

```python
weather = client.get_current_weather(city="Kyiv")

print(weather.temperature)              # 18.5
print(weather.feels_like)               # 17.2
print(weather.humidity)                  # 72
print(weather.pressure)                  # 1013
print(weather.condition.description)     # "scattered clouds"
print(weather.wind.speed)               # 3.6
print(weather.wind.direction)           # 220
print(weather.location.name)            # "Kyiv"
```

Multiple location formats are supported:

```python
client.get_current_weather(city="Lviv")
client.get_current_weather(lat=50.45, lon=30.52)  # Kyiv
client.get_current_weather(city_id=2643743)        # London
client.get_current_weather(zip_code="10001,us")    # New York
```

### 5-Day Forecast

```python
forecast = client.get_forecast(city="Berlin", count=8)  # next 24 hours

print(forecast.location.name)  # "Berlin"

for entry in forecast.entries:
    print(f"{entry.forecast_at}: {entry.temperature}°C — {entry.condition.description}")
    # "2026-04-05 18:00:00: 14.2°C — light rain"
```

## Geocoding

```python
# City name to coordinates
locations = client.geocode("London")
for loc in locations:
    print(f"{loc.name}, {loc.country}: ({loc.latitude}, {loc.longitude})")
    # "London, GB: (51.5074, -0.1278)"

# Coordinates to city name
locations = client.reverse_geocode(lat=48.8566, lon=2.3522)
print(locations[0].name)  # "Paris"
```

## Geomagnetic Storms

Real-time and forecast geomagnetic data from [NOAA Space Weather Prediction Center](https://www.swpc.noaa.gov/) (SWPC). The SDK fetches the planetary Kp index — a global measure of geomagnetic disturbance on a 0-9 scale — and maps it to the NOAA G-scale (G0-G5) with a human-readable `severity` label. A Kp value of 5 or higher indicates an active geomagnetic storm.

| Kp Index | G-Scale | Severity |
|----------|---------|----------|
| 0-4 | G0 | Quiet |
| 5 | G1 | Minor storm |
| 6 | G2 | Moderate storm |
| 7 | G3 | Strong storm |
| 8 | G4 | Severe storm |
| 9 | G5 | Extreme storm |

### Current Conditions

```python
storm = client.get_magnetic_storm()

print(storm.kp_index)          # 5.33
print(storm.g_scale)           # "G1"
print(storm.severity)          # "Minor storm"
print(storm.is_storm)          # True
print(storm.observed_at)       # 2026-04-05 06:00:00+00:00
print(storm.data_age_seconds)  # 847
print(storm.stale)             # False
print(storm.station_count)     # 8
```

The `stale` flag indicates that NOAA was unreachable and the response was served from cache. The `data_age_seconds` field shows how old the observation is.

### 3-Day Magnetic Forecast

The SDK retrieves NOAA's 3-day planetary Kp index forecast, which provides predicted geomagnetic activity in 3-hour intervals. This enables proactive alerting — warn users about upcoming storms before they happen.

Each forecast entry covers a 3-hour window and includes both observed (past) and predicted (future) periods, distinguished by the `is_observed` flag.

```python
forecast = client.get_magnetic_forecast()

for entry in forecast:
    kind = "observed" if entry.is_observed else "predicted"
    print(f"{entry.period_start} — {entry.period_end}: Kp {entry.predicted_kp} — {entry.severity} [{kind}]")
    # "2026-04-05 09:00:00 — 2026-04-05 12:00:00: Kp 5.0 — Minor storm [predicted]"
    if entry.is_storm:
        print("  Storm expected!")  # "  Storm expected!"
```

Find upcoming storms:

```python
upcoming_storms = [e for e in client.get_magnetic_forecast() if e.is_storm and not e.is_observed]

if upcoming_storms:
    first = upcoming_storms[0]
    print(f"Storm predicted at {first.period_start}: Kp {first.predicted_kp} — {first.severity}")
    # "Storm predicted at 2026-04-05 09:00:00: Kp 5.0 — Minor storm"
```

### Data Freshness & Resilience

NOAA SWPC updates the Kp index approximately every 15 minutes. The SDK caches storm data for 10 minutes by default and uses stale-while-revalidate fallback — if NOAA is temporarily unreachable, the last known data is returned with `stale=True` rather than raising an error. Stale data expires after 30 minutes for current conditions and 6 hours for forecasts.

## Health Impact

Assess potential health effects of geomagnetic activity based on the current Kp index.

```python
impact = client.get_storm_health_impact()

print(impact.level)              # "moderate"
print(impact.affected_systems)   # ["cardiovascular", "nervous"]
print(impact.recommendations)    # ["Migraine-prone and cardiovascular-sensitive individuals should monitor symptoms.", ...]
print(impact.disclaimer)         # "Health impact information is for general awareness only..."
```

## Storm Alerts

Location-aware alerts that combine magnetic storm data with latitude-adjusted health impact and aurora visibility.

```python
# Provide coordinates explicitly (Stockholm)
alert = client.get_storm_alert(lat=59.33, lon=18.07)

# Or use auto-location (IP-based)
alert = client.get_storm_alert(auto_locate=True)

print(alert.storm)                # MagneticStorm(kp_index=5.33, ...)
print(alert.health_impact)        # HealthImpact(level="low", ...)
print(alert.location)             # Location(name="Stockholm", ...)
print(alert.aurora_visible)       # True
print(alert.latitude_zone)        # "mid"
```

Health impact is adjusted based on latitude — higher latitudes experience stronger effects during geomagnetic storms.

## Auto-Location

Detect user location from IP address for hands-free queries:

```python
# Client-level auto-locate
client = SkyPulseClient(api_key="key", auto_locate=True)
weather = client.get_current_weather()  # no city needed

# Per-request auto-locate
weather = client.get_current_weather(auto_locate=True)

# Get location directly
location = client.get_location()
print(f"{location.name}, {location.country}: ({location.latitude}, {location.longitude})")
# "Kyiv, UA: (50.4501, 30.5234)"
```

## Caching

```python
from skypulse import SkyPulseClient, CacheConfig

client = SkyPulseClient(
    api_key="your-api-key",
    cache=CacheConfig(enabled=True, ttl=600, max_entries=256),
)

# Second call returns from cache
weather1 = client.get_current_weather(city="Rome")
weather2 = client.get_current_weather(city="Rome")  # instant, from cache

# Force fresh data
weather3 = client.get_current_weather(city="Rome", skip_cache=True)
```

Storm and geolocation data use separate caches with stale-while-revalidate fallback — if the external service is temporarily unavailable, the SDK returns the last known data with a `stale=True` flag.

## Async Usage

```python
import asyncio
from skypulse import AsyncSkyPulseClient, Units

async def main():
    async with AsyncSkyPulseClient(api_key="your-api-key", units=Units.METRIC) as client:
        weather = await client.get_current_weather(city="Lviv")
        print(f"{weather.temperature}°C")  # "12.3°C"

        storm = await client.get_magnetic_storm()
        print(f"{storm.severity} (Kp {storm.kp_index})")  # "Minor storm (Kp 5.33)"

        alert = await client.get_storm_alert(lat=59.33, lon=18.07)  # Stockholm
        print(f"Aurora visible: {alert.aurora_visible}")  # "Aurora visible: True"

asyncio.run(main())
```

All sync methods have async equivalents with identical signatures.

## Error Handling

```python
from skypulse import SkyPulseClient
from skypulse.errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    OpenWeatherError,
)

client = SkyPulseClient(api_key="your-api-key")

try:
    weather = client.get_current_weather(city="Atlantis")
except NotFoundError as e:
    print(f"City not found: {e.message}")  # "City not found: city not found"
except AuthenticationError:
    print("Check your API key")  # "Check your API key"
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")  # "Rate limited. Retry after 60 seconds"
except ServiceUnavailableError:
    print("External service (NOAA/geolocation) is down")  # "External service (NOAA/geolocation) is down"
except OpenWeatherError as e:
    print(f"Something went wrong: {e.message}")  # "Something went wrong: ..."
```

## Configuration

### Unit Systems

```python
from skypulse import Units

# Client-level default
client = SkyPulseClient(api_key="key", units=Units.IMPERIAL)

# Per-request override
weather = client.get_current_weather(city="New York", units=Units.METRIC)
```

| Units | Temperature | Wind Speed |
|-------|-------------|------------|
| `STANDARD` | Kelvin | m/s |
| `METRIC` | Celsius | m/s |
| `IMPERIAL` | Fahrenheit | mph |

### Retry

```python
from skypulse import RetryConfig

client = SkyPulseClient(
    api_key="key",
    retry=RetryConfig(enabled=True, max_retries=3, backoff_factor=0.5),
)
```

Retries on 429 (rate limit), 500, 502, 503 with exponential backoff. Respects `Retry-After` headers.

## API Coverage

| Source | Endpoint | Method |
|--------|----------|--------|
| OpenWeather | Current Weather | `get_current_weather()` |
| OpenWeather | 5-Day Forecast | `get_forecast()` |
| OpenWeather | Direct Geocoding | `geocode()` |
| OpenWeather | Reverse Geocoding | `reverse_geocode()` |
| NOAA SWPC | Planetary K-Index | `get_magnetic_storm()` |
| NOAA SWPC | K-Index Forecast | `get_magnetic_forecast()` |
| ip-api.com | IP Geolocation | `get_location()` |
| Derived | Health Impact | `get_storm_health_impact()` |
| Derived | Storm Alert | `get_storm_alert()` |

## Development

```bash
pip install -e ".[dev]"
pytest
mypy src/skypulse
ruff check src/
```

## License

MIT
