"""Repository for geocoding and location search using Nominatim (OpenStreetMap)."""

import logging
from dataclasses import dataclass
from typing import Any

from app.resources.http_client import HttpClient, HttpClientError

logger = logging.getLogger(__name__)


class GeocodingError(Exception):
    """Raised when geocoding request fails."""

    pass


class LocationNotFoundError(GeocodingError):
    """Raised when location cannot be found."""

    pass


@dataclass
class Beach:
    """Beach location data."""

    name: str
    display_name: str
    lat: float
    lon: float
    city: str | None = None
    country: str | None = None
    osm_id: str | None = None
    osm_type: str | None = None


class GeocodingRepository:
    """Repository for Nominatim geocoding API."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org"
    USER_AGENT = "SurfMCP/1.0 (Surf Conditions Forecast)"

    def __init__(self, http_client: HttpClient | None = None):
        """Initialize repository.

        Args:
            http_client: Optional HTTP client instance
        """
        self._http_client = http_client

    async def _get_client(self) -> HttpClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = HttpClient()
        return self._http_client

    async def find_beaches(self, city: str, country: str | None = None) -> list[Beach]:
        """Find beaches in a city using Nominatim search.

        Args:
            city: City name to search
            country: Optional country name to narrow search

        Returns:
            List of Beach objects found

        Raises:
            GeocodingError: If API request fails
            LocationNotFoundError: If no beaches found
        """
        client = await self._get_client()

        # Build search query
        query_parts = ["beach", city]
        if country:
            query_parts.append(country)
        query = " ".join(query_parts)

        params = {
            "q": query,
            "format": "json",
            "addressdetails": "1",
            "limit": "20",  # Get multiple results
            "featuretype": "natural",  # Focus on natural features
        }

        headers = {"User-Agent": self.USER_AGENT}

        try:
            logger.info(f"Searching beaches in {city}")
            url = f"{self.NOMINATIM_URL}/search"

            # Use GET request with params
            import httpx

            async_client = await client._get_client()
            response = await async_client.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

        except HttpClientError as e:
            raise GeocodingError(f"Failed to search for beaches: {e}") from e
        except Exception as e:
            raise GeocodingError(f"Failed to search for beaches: {e}") from e

        if not results:
            raise LocationNotFoundError(
                f"No beaches found in {city}"
                + (f", {country}" if country else "")
            )

        # Parse results into Beach objects
        beaches = []
        for result in results:
            # Filter for actual beaches
            if "beach" not in result.get("display_name", "").lower():
                continue

            address = result.get("address", {})
            beach = Beach(
                name=result.get("name", "Unnamed Beach"),
                display_name=result.get("display_name", ""),
                lat=float(result.get("lat", 0)),
                lon=float(result.get("lon", 0)),
                city=address.get("city")
                or address.get("town")
                or address.get("village"),
                country=address.get("country"),
                osm_id=str(result.get("osm_id")),
                osm_type=result.get("osm_type"),
            )
            beaches.append(beach)

        if not beaches:
            raise LocationNotFoundError(
                f"No beaches found in {city}"
                + (f", {country}" if country else "")
            )

        logger.info(f"Found {len(beaches)} beaches in {city}")
        return beaches

    async def geocode_beach(
        self, beach_name: str, city: str | None = None, country: str | None = None
    ) -> Beach:
        """Geocode a specific beach by name.

        Args:
            beach_name: Name of the beach
            city: Optional city name to narrow search
            country: Optional country name to narrow search

        Returns:
            Beach object with coordinates

        Raises:
            GeocodingError: If API request fails
            LocationNotFoundError: If beach not found
        """
        client = await self._get_client()

        # Build search query
        query_parts = [beach_name]
        if city:
            query_parts.append(city)
        if country:
            query_parts.append(country)
        query = " ".join(query_parts)

        params = {
            "q": query,
            "format": "json",
            "addressdetails": "1",
            "limit": "1",  # Get best match only
        }

        headers = {"User-Agent": self.USER_AGENT}

        try:
            logger.info(f"Geocoding beach: {beach_name}")
            url = f"{self.NOMINATIM_URL}/search"

            # Use GET request with params
            import httpx

            async_client = await client._get_client()
            response = await async_client.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

        except HttpClientError as e:
            raise GeocodingError(f"Failed to geocode beach: {e}") from e
        except Exception as e:
            raise GeocodingError(f"Failed to geocode beach: {e}") from e

        if not results:
            location_str = beach_name
            if city:
                location_str += f", {city}"
            if country:
                location_str += f", {country}"
            raise LocationNotFoundError(f"Beach not found: {location_str}")

        # Parse first result
        result = results[0]
        address = result.get("address", {})

        beach = Beach(
            name=result.get("name", beach_name),
            display_name=result.get("display_name", ""),
            lat=float(result.get("lat", 0)),
            lon=float(result.get("lon", 0)),
            city=address.get("city") or address.get("town") or address.get("village"),
            country=address.get("country"),
            osm_id=str(result.get("osm_id")),
            osm_type=result.get("osm_type"),
        )

        logger.info(f"Found beach: {beach.name} at ({beach.lat}, {beach.lon})")
        return beach

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.close()

    async def __aenter__(self) -> "GeocodingRepository":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
