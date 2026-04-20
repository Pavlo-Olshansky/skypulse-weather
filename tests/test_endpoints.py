import math

import pytest

from skypulse._endpoints import build_location_params, build_weather_params


class TestBuildLocationParams:
    def test_valid_lat_lon(self):
        result = build_location_params(lat=51.5, lon=-0.12)
        assert result == {"lat": 51.5, "lon": -0.12}

    def test_zero_coordinates(self):
        result = build_location_params(lat=0, lon=0)
        assert result == {"lat": 0, "lon": 0}

    def test_boundary_min(self):
        result = build_location_params(lat=-90, lon=-180)
        assert result == {"lat": -90, "lon": -180}

    def test_boundary_max(self):
        result = build_location_params(lat=90, lon=180)
        assert result == {"lat": 90, "lon": 180}

    def test_lat_too_high(self):
        with pytest.raises(ValueError, match="lat must be between -90 and 90"):
            build_location_params(lat=91, lon=0)

    def test_lat_too_low(self):
        with pytest.raises(ValueError, match="lat must be between -90 and 90"):
            build_location_params(lat=-91, lon=0)

    def test_lon_too_high(self):
        with pytest.raises(ValueError, match="lon must be between -180 and 180"):
            build_location_params(lat=0, lon=181)

    def test_lon_too_low(self):
        with pytest.raises(ValueError, match="lon must be between -180 and 180"):
            build_location_params(lat=0, lon=-181)

    def test_lat_nan(self):
        with pytest.raises(ValueError, match="finite"):
            build_location_params(lat=float("nan"), lon=0)

    def test_lon_nan(self):
        with pytest.raises(ValueError, match="finite"):
            build_location_params(lat=0, lon=float("nan"))

    def test_lat_infinity(self):
        with pytest.raises(ValueError, match="finite"):
            build_location_params(lat=math.inf, lon=0)

    def test_lon_neg_infinity(self):
        with pytest.raises(ValueError, match="finite"):
            build_location_params(lat=0, lon=-math.inf)

    def test_city_param(self):
        result = build_location_params(city="London")
        assert result == {"q": "London"}

    def test_zip_param(self):
        result = build_location_params(zip_code="10001,US")
        assert result == {"zip": "10001,US"}

    def test_missing_all_params(self):
        with pytest.raises(ValueError, match="Exactly one location parameter"):
            build_location_params()

    def test_multiple_params(self):
        with pytest.raises(ValueError, match="Exactly one location parameter"):
            build_location_params(city="London", lat=51.5, lon=-0.12)

    def test_lat_without_lon(self):
        with pytest.raises(ValueError, match="Both lat and lon"):
            build_location_params(lat=51.5)

    def test_lon_without_lat(self):
        with pytest.raises(ValueError, match="Both lat and lon"):
            build_location_params(lon=-0.12)


class TestBuildWeatherParams:
    def test_with_valid_coordinates(self):
        result = build_weather_params(
            "test-key", units="metric", lang="en", lat=51.5, lon=-0.12
        )
        assert result["lat"] == 51.5
        assert result["lon"] == -0.12
        assert result["appid"] == "test-key"

    def test_invalid_coordinates_propagate(self):
        with pytest.raises(ValueError, match="lat must be between"):
            build_weather_params(
                "test-key", units="metric", lang="en", lat=91, lon=0
            )
