"""HTTP client with retry logic and timeout handling."""

import asyncio
import logging
from typing import Any

import httpx

from app.resources.config import get_settings

logger = logging.getLogger(__name__)


class HttpClientError(Exception):
    """Base exception for HTTP client errors."""

    pass


class HttpTimeoutError(HttpClientError):
    """Raised when request times out after all retries."""

    pass


class HttpRequestError(HttpClientError):
    """Raised when request fails with non-retryable error."""

    pass


class HttpClient:
    """Async HTTP client with exponential backoff retry."""

    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "User-Agent": "SurfMCP/1.0",
    }

    def __init__(
        self,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        """Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        settings = get_settings()
        self.timeout = timeout or settings.http_timeout
        self.max_retries = max_retries or settings.max_retries
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.DEFAULT_HEADERS,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make POST request with retry logic.

        Args:
            url: Request URL
            json: JSON body to send
            headers: Additional headers

        Returns:
            Response JSON as dictionary

        Raises:
            HttpTimeoutError: If all retries fail due to timeout
            HttpRequestError: If request fails with non-retryable error
        """
        client = await self._get_client()
        request_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    url,
                    json=json,
                    headers=request_headers,
                )
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Request timeout (attempt {attempt + 1}/{self.max_retries}), "
                    f"retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error: {e.response.status_code} - {e.response.text}")
                    raise HttpRequestError(
                        f"Request failed with status {e.response.status_code}: {e.response.text}"
                    ) from e

                # Retry server errors (5xx)
                last_exception = e
                wait_time = 2**attempt
                logger.warning(
                    f"Server error {e.response.status_code} (attempt {attempt + 1}/{self.max_retries}), "
                    f"retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

            except httpx.RequestError as e:
                last_exception = e
                wait_time = 2**attempt
                logger.warning(
                    f"Request error (attempt {attempt + 1}/{self.max_retries}): {e}, "
                    f"retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

        # All retries exhausted
        if isinstance(last_exception, httpx.TimeoutException):
            raise HttpTimeoutError(
                f"Request timed out after {self.max_retries} attempts"
            ) from last_exception

        raise HttpRequestError(
            f"Request failed after {self.max_retries} attempts: {last_exception}"
        ) from last_exception

    async def __aenter__(self) -> "HttpClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
