"""Surf analysis service with business rules for surf conditions."""

import math
from dataclasses import dataclass
from enum import Enum


class WindType(str, Enum):
    """Wind type relative to wave direction."""

    OFFSHORE = "offshore"
    ONSHORE = "onshore"
    CROSS = "cross"


@dataclass
class QualityIndicators:
    """Quality indicators for surf conditions."""

    is_offshore: bool
    good_period: bool  # Period >= 10 seconds
    surfable: bool


@dataclass
class AnalyzedConditions:
    """Analyzed surf conditions with quality metrics."""

    wind_speed_ms: float
    wind_direction_deg: float
    wind_type: WindType
    quality_indicators: QualityIndicators


class SurfAnalyzerService:
    """Service for analyzing surf conditions and quality."""

    # Thresholds for surf quality
    MIN_SURFABLE_HEIGHT_M = 0.5
    MIN_SURFABLE_PERIOD_S = 8.0
    GOOD_PERIOD_THRESHOLD_S = 10.0
    MAX_WIND_SPEED_FOR_QUALITY_MS = 10.0

    # Wind direction thresholds (degrees from wave direction)
    OFFSHORE_MIN_ANGLE = 135
    OFFSHORE_MAX_ANGLE = 225
    ONSHORE_MAX_ANGLE = 45

    @classmethod
    def calculate_wind_from_components(
        cls,
        wind_u: float | None,
        wind_v: float | None,
    ) -> tuple[float, float]:
        """Calculate wind speed and direction from u/v components.

        Args:
            wind_u: West-to-East wind component (m/s)
            wind_v: South-to-North wind component (m/s)

        Returns:
            Tuple of (wind_speed_ms, wind_direction_deg)
            Direction is where wind comes FROM (meteorological convention)
        """
        if wind_u is None or wind_v is None:
            return 0.0, 0.0

        # Calculate speed
        speed = math.sqrt(wind_u**2 + wind_v**2)

        # Calculate direction (where wind is going TO)
        direction_to = math.degrees(math.atan2(wind_u, wind_v))

        # Convert to where wind comes FROM (add 180°)
        direction_from = (direction_to + 180) % 360

        return round(speed, 2), round(direction_from, 1)

    @classmethod
    def analyze_wind_type(
        cls,
        wind_direction_deg: float,
        wave_direction_deg: float,
    ) -> WindType:
        """Analyze wind type relative to wave direction.

        Offshore wind blows from land to sea (opposite to wave direction),
        which creates cleaner, more organized waves.

        Args:
            wind_direction_deg: Direction wind comes FROM (0-360°)
            wave_direction_deg: Direction waves come FROM (0-360°)

        Returns:
            WindType classification
        """
        # Calculate angle difference
        diff = abs(wind_direction_deg - wave_direction_deg)

        # Normalize to 0-180 range
        if diff > 180:
            diff = 360 - diff

        # Offshore: wind blowing opposite to wave direction (135-225° difference)
        # This means wind is blowing from land toward the ocean
        if cls.OFFSHORE_MIN_ANGLE <= diff + 180 <= cls.OFFSHORE_MAX_ANGLE + 180:
            # Recalculate: if wind opposes wave direction
            if diff >= 135:
                return WindType.OFFSHORE

        # More direct check for offshore
        # Offshore means wind and wave directions are roughly opposite
        if 135 <= diff <= 180:
            return WindType.OFFSHORE

        # Onshore: wind blowing same direction as waves (< 45° difference)
        if diff <= cls.ONSHORE_MAX_ANGLE:
            return WindType.ONSHORE

        # Cross-shore: anything in between
        return WindType.CROSS

    @classmethod
    def is_surfable(
        cls,
        wave_height_m: float | None,
        wave_period_s: float | None,
        wind_speed_ms: float | None = None,
    ) -> bool:
        """Determine if conditions are surfable.

        Args:
            wave_height_m: Wave height in meters
            wave_period_s: Wave period in seconds
            wind_speed_ms: Wind speed in m/s (optional)

        Returns:
            True if conditions meet minimum surfing requirements
        """
        if wave_height_m is None or wave_period_s is None:
            return False

        # Check minimum height
        if wave_height_m < cls.MIN_SURFABLE_HEIGHT_M:
            return False

        # Check minimum period
        if wave_period_s < cls.MIN_SURFABLE_PERIOD_S:
            return False

        return True

    @classmethod
    def calculate_quality_indicators(
        cls,
        wave_height_m: float | None,
        wave_period_s: float | None,
        wind_type: WindType,
        wind_speed_ms: float | None = None,
    ) -> QualityIndicators:
        """Calculate quality indicators for surf conditions.

        Args:
            wave_height_m: Wave height in meters
            wave_period_s: Wave period in seconds
            wind_type: Analyzed wind type
            wind_speed_ms: Wind speed in m/s

        Returns:
            QualityIndicators with analysis results
        """
        is_offshore = wind_type == WindType.OFFSHORE

        good_period = (
            wave_period_s is not None and wave_period_s >= cls.GOOD_PERIOD_THRESHOLD_S
        )

        surfable = cls.is_surfable(wave_height_m, wave_period_s, wind_speed_ms)

        return QualityIndicators(
            is_offshore=is_offshore,
            good_period=good_period,
            surfable=surfable,
        )

    @classmethod
    def analyze_conditions(
        cls,
        wind_u: float | None,
        wind_v: float | None,
        wave_direction_deg: float | None,
        wave_height_m: float | None,
        wave_period_s: float | None,
    ) -> AnalyzedConditions:
        """Perform complete analysis of surf conditions.

        Args:
            wind_u: West-to-East wind component (m/s)
            wind_v: South-to-North wind component (m/s)
            wave_direction_deg: Direction waves come FROM
            wave_height_m: Wave height in meters
            wave_period_s: Wave period in seconds

        Returns:
            AnalyzedConditions with full analysis
        """
        # Calculate wind speed and direction
        wind_speed_ms, wind_direction_deg = cls.calculate_wind_from_components(
            wind_u, wind_v
        )

        # Determine wind type
        if wave_direction_deg is not None:
            wind_type = cls.analyze_wind_type(wind_direction_deg, wave_direction_deg)
        else:
            wind_type = WindType.CROSS  # Default if no wave direction

        # Calculate quality indicators
        quality_indicators = cls.calculate_quality_indicators(
            wave_height_m=wave_height_m,
            wave_period_s=wave_period_s,
            wind_type=wind_type,
            wind_speed_ms=wind_speed_ms,
        )

        return AnalyzedConditions(
            wind_speed_ms=wind_speed_ms,
            wind_direction_deg=wind_direction_deg,
            wind_type=wind_type,
            quality_indicators=quality_indicators,
        )
