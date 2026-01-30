"""MCP tools for surf conditions."""

import logging
from dataclasses import asdict
from typing import Any

from app.application.use_cases.get_surf_conditions import GetSurfConditionsUseCase
from app.repository.geocoding_repository import (
    GeocodingError,
    GeocodingRepository,
    LocationNotFoundError,
)
from app.repository.windy_repository import WindyApiError, WindyNoCoverageError

logger = logging.getLogger(__name__)


def register_tools(mcp) -> None:
    """Register surf tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()
    async def get_surf_conditions(
        lat: float,
        lon: float,
        hours_ahead: int = 24,
    ) -> dict[str, Any]:
        """Get surf conditions forecast for a specific location.

        Fetches wave and wind data from Windy API and returns analyzed
        surf conditions including wave height, period, direction,
        wind analysis (offshore/onshore/cross), and quality indicators.

        Args:
            lat: Latitude of the surf spot (-90 to 90)
            lon: Longitude of the surf spot (-180 to 180)
            hours_ahead: Hours of forecast to return (default 24, max 384)

        Returns:
            Dictionary containing:
            - location: {lat, lon}
            - forecasts: List of hourly forecasts with:
                - timestamp: ISO 8601 timestamp
                - wave_height_m: Wave height in meters
                - wave_period_s: Wave period in seconds
                - wave_direction_deg: Direction waves come from (degrees)
                - swell_height_m: Primary swell height in meters
                - swell_period_s: Primary swell period in seconds
                - swell_direction_deg: Primary swell direction (degrees)
                - wind_speed_ms: Wind speed in m/s
                - wind_direction_deg: Direction wind comes from (degrees)
                - wind_type: "offshore", "onshore", or "cross"
                - quality_indicators: {is_offshore, good_period, surfable}
            - metadata: {model, generated_at}

        Example:
            >>> get_surf_conditions(-34.6037, -58.3816, 48)
            {
                "location": {"lat": -34.6037, "lon": -58.3816},
                "forecasts": [
                    {
                        "timestamp": "2026-01-29T12:00:00+00:00",
                        "wave_height_m": 1.8,
                        "wave_period_s": 12.5,
                        "wave_direction_deg": 285,
                        "wind_type": "offshore",
                        "quality_indicators": {
                            "is_offshore": true,
                            "good_period": true,
                            "surfable": true
                        }
                    }
                ],
                "metadata": {"model": "gfsWave", "generated_at": "..."}
            }
        """
        try:
            async with GetSurfConditionsUseCase() as use_case:
                result = await use_case.execute(lat, lon, hours_ahead)

                # Convert dataclass to dict
                return {
                    "location": result.location,
                    "forecasts": [asdict(f) for f in result.forecasts],
                    "metadata": result.metadata,
                }

        except ValueError as e:
            logger.warning(f"Invalid input: {e}")
            return {
                "error": str(e),
                "error_type": "validation_error",
            }

        except WindyNoCoverageError as e:
            logger.warning(f"No coverage: {e}")
            return {
                "error": str(e),
                "error_type": "no_coverage",
                "hint": "GFS Wave model excludes Hudson Bay, Black Sea, Caspian Sea, and Arctic Ocean.",
            }

        except WindyApiError as e:
            logger.error(f"Windy API error: {e}")
            return {
                "error": str(e),
                "error_type": "api_error",
                "hint": "Check if WINDY_API_KEY is configured correctly.",
            }

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "internal_error",
            }

    @mcp.tool()
    async def find_beaches(
        city: str,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Find beaches in a city using OpenStreetMap data.

        Searches for beaches in a specific city and returns a list
        with names and coordinates that can be used with get_surf_conditions
        or get_surf_conditions_by_beach.

        Args:
            city: Name of the city to search (e.g., "Mar del Plata", "Sydney")
            country: Optional country name to narrow search (e.g., "Argentina", "Australia")

        Returns:
            Dictionary containing:
            - beaches: List of beach objects with:
                - name: Beach name
                - display_name: Full display name with location
                - lat: Latitude
                - lon: Longitude
                - city: City name
                - country: Country name
            - count: Total number of beaches found

        Example:
            >>> find_beaches("Mar del Plata", "Argentina")
            {
                "beaches": [
                    {
                        "name": "Playa Grande",
                        "display_name": "Playa Grande, Mar del Plata, Argentina",
                        "lat": -38.012,
                        "lon": -57.535,
                        "city": "Mar del Plata",
                        "country": "Argentina"
                    },
                    ...
                ],
                "count": 5
            }
        """
        try:
            async with GeocodingRepository() as repo:
                beaches = await repo.find_beaches(city, country)

                return {
                    "beaches": [
                        {
                            "name": beach.name,
                            "display_name": beach.display_name,
                            "lat": beach.lat,
                            "lon": beach.lon,
                            "city": beach.city,
                            "country": beach.country,
                        }
                        for beach in beaches
                    ],
                    "count": len(beaches),
                }

        except LocationNotFoundError as e:
            logger.warning(f"Location not found: {e}")
            return {
                "error": str(e),
                "error_type": "not_found",
                "hint": "Try a different city name or check spelling. Example: 'Mar del Plata', 'Sydney'",
            }

        except GeocodingError as e:
            logger.error(f"Geocoding error: {e}")
            return {
                "error": str(e),
                "error_type": "geocoding_error",
                "hint": "There was an error with the geocoding service. Please try again later.",
            }

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "internal_error",
            }

    @mcp.tool()
    async def get_surf_conditions_by_beach(
        beach_name: str,
        city: str | None = None,
        country: str | None = None,
        hours_ahead: int = 24,
    ) -> dict[str, Any]:
        """Get surf conditions forecast for a specific beach by name.

        Automatically finds the beach coordinates and returns surf forecast.
        This is a convenience tool that combines geocoding + forecast.

        Args:
            beach_name: Name of the beach (e.g., "Playa Grande", "Waikiki Beach")
            city: Optional city name to narrow search (e.g., "Mar del Plata")
            country: Optional country name to narrow search (e.g., "Argentina")
            hours_ahead: Hours of forecast to return (default 24, max 384)

        Returns:
            Dictionary containing:
            - beach: {name, display_name, lat, lon, city, country}
            - location: {lat, lon}
            - forecasts: List of hourly forecasts (same format as get_surf_conditions)
            - metadata: {model, generated_at}

        Example:
            >>> get_surf_conditions_by_beach("Playa Grande", "Mar del Plata")
            {
                "beach": {
                    "name": "Playa Grande",
                    "display_name": "Playa Grande, Mar del Plata, Argentina",
                    "lat": -38.012,
                    "lon": -57.535
                },
                "location": {"lat": -38.012, "lon": -57.535},
                "forecasts": [...],
                "metadata": {"model": "gfsWave", "generated_at": "..."}
            }
        """
        try:
            # Step 1: Geocode the beach
            async with GeocodingRepository() as geo_repo:
                beach = await geo_repo.geocode_beach(beach_name, city, country)

            logger.info(
                f"Found beach: {beach.name} at ({beach.lat}, {beach.lon}), "
                f"fetching surf conditions..."
            )

            # Step 2: Get surf conditions
            async with GetSurfConditionsUseCase() as use_case:
                result = await use_case.execute(beach.lat, beach.lon, hours_ahead)

                # Return combined data
                return {
                    "beach": {
                        "name": beach.name,
                        "display_name": beach.display_name,
                        "lat": beach.lat,
                        "lon": beach.lon,
                        "city": beach.city,
                        "country": beach.country,
                    },
                    "location": result.location,
                    "forecasts": [asdict(f) for f in result.forecasts],
                    "metadata": result.metadata,
                }

        except LocationNotFoundError as e:
            logger.warning(f"Beach not found: {e}")
            return {
                "error": str(e),
                "error_type": "beach_not_found",
                "hint": "Try using find_beaches first to see available beaches, or check the beach name spelling.",
            }

        except GeocodingError as e:
            logger.error(f"Geocoding error: {e}")
            return {
                "error": str(e),
                "error_type": "geocoding_error",
                "hint": "There was an error finding the beach location. Please try again later.",
            }

        except ValueError as e:
            logger.warning(f"Invalid input: {e}")
            return {
                "error": str(e),
                "error_type": "validation_error",
            }

        except WindyNoCoverageError as e:
            logger.warning(f"No coverage: {e}")
            return {
                "error": str(e),
                "error_type": "no_coverage",
                "hint": "GFS Wave model excludes Hudson Bay, Black Sea, Caspian Sea, and Arctic Ocean.",
            }

        except WindyApiError as e:
            logger.error(f"Windy API error: {e}")
            return {
                "error": str(e),
                "error_type": "api_error",
                "hint": "Check if WINDY_API_KEY is configured correctly.",
            }

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "error_type": "internal_error",
            }
