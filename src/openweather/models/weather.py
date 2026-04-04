from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openweather.models.location import Location


@dataclass(frozen=True)
class Condition:
    """Weather condition descriptor (e.g. "Rain", "Clear").

    Attributes:
        id: OpenWeather condition ID.
        main: Short condition group name (e.g. ``"Clouds"``).
        description: Human-readable description (e.g. ``"overcast clouds"``).
        icon: Icon code for the condition (e.g. ``"04d"``).
    """

    id: int
    main: str
    description: str
    icon: str


@dataclass(frozen=True)
class Wind:
    """Wind measurement data.

    Attributes:
        speed: Wind speed (units depend on the ``Units`` setting).
        direction: Wind direction in meteorological degrees.
        gust: Wind gust speed, or ``None`` if unavailable.
    """

    speed: float
    direction: int
    gust: float | None = None


@dataclass(frozen=True)
class Weather:
    """Current weather observation for a single location.

    Attributes:
        location: The location this observation belongs to.
        temperature: Current temperature.
        feels_like: Perceived temperature accounting for wind and humidity.
        temp_min: Minimum observed temperature at the moment.
        temp_max: Maximum observed temperature at the moment.
        humidity: Humidity percentage (0--100).
        pressure: Atmospheric pressure in hPa.
        visibility: Visibility in metres.
        wind: Wind data.
        clouds: Cloudiness percentage (0--100).
        condition: Weather condition descriptor.
        observed_at: UTC timestamp of the observation.
    """

    location: Location
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    pressure: int
    visibility: int
    wind: Wind
    clouds: int
    condition: Condition
    observed_at: datetime
