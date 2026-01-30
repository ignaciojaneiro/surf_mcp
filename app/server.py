"""MCP Server entry point for Surf Conditions API."""

import logging
import os
import sys

from fastmcp import FastMCP

from app.resources.config import get_settings
from app.tools.surf_tools import register_tools

# Configure logging to stderr (required for STDIO transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP(
    name="surf-conditions",
    instructions="""
    This MCP server provides surf conditions forecasts using Windy Point Forecast API
    and beach location search using OpenStreetMap.
    
    Available tools:
    - find_beaches: Search for beaches in a city
    - get_surf_conditions_by_beach: Get surf forecast by beach name
    - get_surf_conditions: Get surf forecast by coordinates
    
    Typical workflow:
    1. Use find_beaches("Mar del Plata") to discover available beaches
    2. Use get_surf_conditions_by_beach("Playa Grande") to get the forecast
    
    The forecast includes:
    - Wave height, period, and direction
    - Primary swell data
    - Wind speed and direction
    - Wind type analysis (offshore/onshore/cross)
    - Quality indicators for surfing conditions
    
    Offshore wind (blowing from land to sea) creates cleaner, more organized waves.
    A period >= 10 seconds indicates quality ground swell.
    Surfable conditions require minimum 0.5m height and 8s period.
    """,
)

# Register tools
register_tools(mcp)


# Add health check endpoint for Railway
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Railway deployment."""
    from starlette.responses import JSONResponse

    settings = get_settings()
    has_api_key = bool(settings.windy_api_key)

    return JSONResponse(
        {
            "status": "healthy",
            "service": "surf-conditions",
            "windy_api_configured": has_api_key,
        }
    )


def main():
    """Run the MCP server."""
    settings = get_settings()

    # Log configuration (without sensitive data)
    logger.info("Starting Surf Conditions MCP Server")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Windy API configured: {bool(settings.windy_api_key)}")

    # Determine transport based on environment
    # Use HTTP for Railway/production, STDIO for local development
    transport = os.getenv("MCP_TRANSPORT", "http")

    if transport == "stdio":
        logger.info("Running with STDIO transport (local development)")
        mcp.run(transport="stdio")
    else:
        port = int(os.getenv("PORT", settings.port))
        logger.info(f"Running with HTTP transport on port {port}")
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=port,
        )


if __name__ == "__main__":
    main()
