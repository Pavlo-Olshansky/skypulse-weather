from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    """Geographic location returned by the API or geocoding endpoints.

    Attributes:
        name: City or place name.
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        country: ISO 3166 country code.
        state: State or region name, if available.
    """

    name: str
    latitude: float
    longitude: float
    country: str
    state: str | None = None
    source: str = "explicit"
