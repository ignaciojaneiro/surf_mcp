"""Use case for getting surf conditions forecast."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.application.services.surf_analyzer import SurfAnalyzerService
from app.repository.windy_repository import (
    WindyRepository,
    WindyWaveData,
    WindyWindData,
)

logger = logging.getLogger(__name__)


@dataclass
class SurfForecast:
    """Single surf forecast entry."""

    timestamp: str
    wave_height_m: float | None
    wave_period_s: float | None
    wave_direction_deg: float | None
    swell_height_m: float | None
    swell_period_s: float | None
    swell_direction_deg: float | None
    wind_speed_ms: float
    wind_direction_deg: float
    wind_type: str
    quality_indicators: dict[str, bool]


@dataclass
class SurfConditionsResponse:
    """Complete surf conditions response."""

    location: dict[str, float]
    forecasts: list[SurfForecast]
    metadata: dict[str, str]


class GetSurfConditionsUseCase:
    """Use case for fetching and analyzing surf conditions."""

    def __init__(self, repository: WindyRepository | None = None):
        """Initialize use case.

        Args:
            repository: Optional WindyRepository instance
        """
        self._repository = repository

    async def _get_repository(self) -> WindyRepository:
        """Get or create repository."""
        if self._repository is None:
            self._repository = WindyRepository()
        return self._repository

    def _validate_coordinates(self, lat: float, lon: float) -> None:
        """Validate coordinate ranges.

        Args:
            lat: Latitude
            lon: Longitude

        Raises:
            ValueError: If coordinates are out of range
        """
        if not -90 <= lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
        if not -180 <= lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180, got {lon}")

    def _timestamp_to_iso(self, ts_ms: int) -> str:
        """Convert Unix timestamp (ms) to ISO 8601 string.

        Args:
            ts_ms: Timestamp in milliseconds

        Returns:
            ISO 8601 formatted string
        """
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        return dt.isoformat()

    def _get_value_at_index(
        self, data: list[Any], index: int, default: Any = None
    ) -> Any:
        """Safely get value at index from list.

        Args:
            data: List to get value from
            index: Index to access
            default: Default value if index out of range

        Returns:
            Value at index or default
        """
        if index < len(data):
            return data[index]
        return default

    def _merge_forecasts(
        self,
        wave_data: WindyWaveData,
        wind_data: WindyWindData,
        hours_ahead: int,
    ) -> list[SurfForecast]:
        """Merge wave and wind data into forecast entries.

        Args:
            wave_data: Raw wave data from Windy
            wind_data: Raw wind data from Windy
            hours_ahead: Maximum hours to include

        Returns:
            List of SurfForecast entries
        """
        forecasts: list[SurfForecast] = []

        # Use wave timestamps as base (they're usually same as wind)
        timestamps = wave_data.timestamps

        # Filter by hours_ahead
        now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
        max_ms = now_ms + (hours_ahead * 3600 * 1000)

        for i, ts in enumerate(timestamps):
            if ts > max_ms:
                break

            # Get wave data at index
            wave_height = self._get_value_at_index(wave_data.wave_heights, i)
            wave_period = self._get_value_at_index(wave_data.wave_periods, i)
            wave_direction = self._get_value_at_index(wave_data.wave_directions, i)

            # Get primary swell data
            swell_height = self._get_value_at_index(wave_data.swell1_heights, i)
            swell_period = self._get_value_at_index(wave_data.swell1_periods, i)
            swell_direction = self._get_value_at_index(wave_data.swell1_directions, i)

            # Get wind components at index
            wind_u = self._get_value_at_index(wind_data.wind_u, i)
            wind_v = self._get_value_at_index(wind_data.wind_v, i)

            # Analyze conditions
            analysis = SurfAnalyzerService.analyze_conditions(
                wind_u=wind_u,
                wind_v=wind_v,
                wave_direction_deg=wave_direction,
                wave_height_m=wave_height,
                wave_period_s=wave_period,
            )

            forecast = SurfForecast(
                timestamp=self._timestamp_to_iso(ts),
                wave_height_m=round(wave_height, 2) if wave_height else None,
                wave_period_s=round(wave_period, 1) if wave_period else None,
                wave_direction_deg=round(wave_direction, 0) if wave_direction else None,
                swell_height_m=round(swell_height, 2) if swell_height else None,
                swell_period_s=round(swell_period, 1) if swell_period else None,
                swell_direction_deg=round(swell_direction, 0) if swell_direction else None,
                wind_speed_ms=analysis.wind_speed_ms,
                wind_direction_deg=analysis.wind_direction_deg,
                wind_type=analysis.wind_type.value,
                quality_indicators={
                    "is_offshore": analysis.quality_indicators.is_offshore,
                    "good_period": analysis.quality_indicators.good_period,
                    "surfable": analysis.quality_indicators.surfable,
                },
            )
            forecasts.append(forecast)

        return forecasts

    async def execute(
        self,
        lat: float,
        lon: float,
        hours_ahead: int = 24,
    ) -> SurfConditionsResponse:
        """Execute the use case to get surf conditions.

        Args:
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            hours_ahead: Hours of forecast to return (default 24, max 384)

        Returns:
            SurfConditionsResponse with normalized forecast data

        Raises:
            ValueError: If coordinates are invalid
            WindyApiError: If API request fails
        """
        # Validate inputs
        self._validate_coordinates(lat, lon)
        hours_ahead = min(max(hours_ahead, 1), 384)  # Clamp to valid range

        repository = await self._get_repository()

        # Fetch wave and wind data in parallel
        logger.info(f"Fetching surf conditions for ({lat}, {lon})")

        wave_data = await repository.get_wave_forecast(lat, lon)
        wind_data = await repository.get_wind_forecast(lat, lon)

        # Merge and analyze forecasts
        forecasts = self._merge_forecasts(wave_data, wind_data, hours_ahead)

        return SurfConditionsResponse(
            location={"lat": lat, "lon": lon},
            forecasts=forecasts,
            metadata={
                "model": "gfsWave",
                "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            },
        )

    async def close(self) -> None:
        """Close repository."""
        if self._repository:
            await self._repository.close()

    async def __aenter__(self) -> "GetSurfConditionsUseCase":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
