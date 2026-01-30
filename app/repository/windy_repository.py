"""Repository for accessing Windy Point Forecast API."""

import logging
from dataclasses import dataclass
from typing import Any

from app.resources.config import get_settings
from app.resources.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class WindyApiError(Exception):
    """Raised when Windy API request fails."""

    pass


class WindyNoCoverageError(WindyApiError):
    """Raised when location has no GFS Wave coverage."""

    pass


@dataclass
class WindyWaveData:
    """Raw wave data from Windy API."""

    timestamps: list[int]  # Unix timestamps in milliseconds
    wave_heights: list[float | None]
    wave_periods: list[float | None]
    wave_directions: list[float | None]
    swell1_heights: list[float | None]
    swell1_periods: list[float | None]
    swell1_directions: list[float | None]
    swell2_heights: list[float | None]
    swell2_periods: list[float | None]
    swell2_directions: list[float | None]


@dataclass
class WindyWindData:
    """Raw wind data from Windy API."""

    timestamps: list[int]  # Unix timestamps in milliseconds
    wind_u: list[float | None]  # West-to-East component (m/s)
    wind_v: list[float | None]  # South-to-North component (m/s)


class WindyRepository:
    """Repository for Windy Point Forecast API."""

    # Wave parameters for gfsWave model
    WAVE_PARAMETERS = ["waves", "swell1", "swell2"]

    # Wind parameters for gfs model
    WIND_PARAMETERS = ["wind"]

    def __init__(self, http_client: HttpClient | None = None):
        """Initialize repository.

        Args:
            http_client: Optional HTTP client instance
        """
        self._http_client = http_client
        self._settings = get_settings()

    async def _get_client(self) -> HttpClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = HttpClient()
        return self._http_client

    def _validate_api_key(self) -> None:
        """Validate that API key is configured."""
        if not self._settings.windy_api_key:
            raise WindyApiError(
                "WINDY_API_KEY environment variable is not set. "
                "Please configure your Windy API key."
            )

    async def get_wave_forecast(self, lat: float, lon: float) -> WindyWaveData:
        """Fetch wave forecast from Windy API using gfsWave model.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            WindyWaveData with wave forecast data

        Raises:
            WindyApiError: If API request fails
            WindyNoCoverageError: If location has no GFS Wave coverage
        """
        self._validate_api_key()

        client = await self._get_client()

        payload = {
            "lat": round(lat, 2),
            "lon": round(lon, 2),
            "model": "gfsWave",
            "parameters": self.WAVE_PARAMETERS,
            "levels": ["surface"],  # Required by Windy API even for wave parameters
            "key": self._settings.windy_api_key,
        }

        logger.debug(f"Wave forecast request payload: {payload}")
        
        try:
            response = await client.post(self._settings.windy_api_url, json=payload)
        except HttpClientError as e:
            error_msg = str(e).lower()
            # Log the full error for debugging
            logger.error(f"Windy API wave error for ({lat}, {lon}): {e}")
            
            # Check if it's a coverage issue based on error message
            if "400" in str(e):
                # Check for specific coverage-related errors
                if any(keyword in error_msg for keyword in ["coverage", "no data", "not available", "no forecast"]):
                    raise WindyNoCoverageError(
                        f"Location ({lat}, {lon}) may not have GFS Wave coverage. "
                        "GFS Wave excludes Hudson Bay, Black Sea, Caspian Sea, and most Arctic Ocean."
                    ) from e
                # For other 400 errors, provide more details
                raise WindyApiError(
                    f"Windy API wave request failed for ({lat}, {lon}): {e}"
                ) from e
            raise WindyApiError(f"Failed to fetch wave forecast: {e}") from e

        return self._parse_wave_response(response)

    async def get_wind_forecast(self, lat: float, lon: float) -> WindyWindData:
        """Fetch wind forecast from Windy API using gfs model.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)

        Returns:
            WindyWindData with wind forecast data

        Raises:
            WindyApiError: If API request fails
        """
        self._validate_api_key()

        client = await self._get_client()

        payload = {
            "lat": round(lat, 2),
            "lon": round(lon, 2),
            "model": "gfs",
            "parameters": self.WIND_PARAMETERS,
            "levels": ["surface"],
            "key": self._settings.windy_api_key,
        }

        try:
            response = await client.post(self._settings.windy_api_url, json=payload)
        except HttpClientError as e:
            raise WindyApiError(f"Failed to fetch wind forecast: {e}") from e

        return self._parse_wind_response(response)

    def _parse_wave_response(self, response: dict[str, Any]) -> WindyWaveData:
        """Parse Windy wave API response.

        Args:
            response: Raw API response

        Returns:
            Parsed WindyWaveData
        """
        timestamps = response.get("ts", [])

        return WindyWaveData(
            timestamps=timestamps,
            wave_heights=response.get("waves_height-surface", []),
            wave_periods=response.get("waves_period-surface", []),
            wave_directions=response.get("waves_direction-surface", []),
            swell1_heights=response.get("swell1_height-surface", []),
            swell1_periods=response.get("swell1_period-surface", []),
            swell1_directions=response.get("swell1_direction-surface", []),
            swell2_heights=response.get("swell2_height-surface", []),
            swell2_periods=response.get("swell2_period-surface", []),
            swell2_directions=response.get("swell2_direction-surface", []),
        )

    def _parse_wind_response(self, response: dict[str, Any]) -> WindyWindData:
        """Parse Windy wind API response.

        Args:
            response: Raw API response

        Returns:
            Parsed WindyWindData
        """
        timestamps = response.get("ts", [])

        return WindyWindData(
            timestamps=timestamps,
            wind_u=response.get("wind_u-surface", []),
            wind_v=response.get("wind_v-surface", []),
        )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.close()

    async def __aenter__(self) -> "WindyRepository":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
