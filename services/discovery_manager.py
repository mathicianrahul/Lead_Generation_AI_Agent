"""
LeadPilot AI — Discovery Manager & Provider Orchestrator
Coordinates Google Places API and OpenStreetMap Overpass API with intelligent fallback,
error categorization, and unified lead normalization.
"""
from typing import Dict, Any, List, Optional, Tuple

from config.settings import settings
from config.logging_config import logger
from services.google_places_service import google_places_service, GooglePlacesService
from services.osm_service import osm_service, OpenStreetMapService


class DiscoveryManager:
    """
    Unified manager for Business Discovery.
    Supports user-selected providers ('google', 'osm', 'auto') with automatic fallback.
    """

    def __init__(
        self,
        google_service: GooglePlacesService = google_places_service,
        osm_svc: OpenStreetMapService = osm_service
    ):
        self.google_service = google_service
        self.osm_service = osm_svc

    def discover_businesses(
        self,
        query: str,
        location: str = "",
        area: str = "",
        country: str = "India",
        max_results: int = 20,
        provider: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """
        Executes discovery according to the selected provider or automatic fallback policy.
        Returns:
            (records, api_calls_made, error_message_if_any)
        """
        active_provider = (provider or settings.discovery_provider or "auto").strip().lower()

        # 1. OpenStreetMap only
        if active_provider in ("osm", "openstreetmap"):
            logger.info("DiscoveryManager executing OpenStreetMap Overpass search for '%s' in '%s'", query, location)
            return self.osm_service.search_places(
                query=query,
                location=location,
                area=area,
                country=country,
                max_results=max_results
            )

        # 2. Google Places only
        if active_provider in ("google", "google_places"):
            logger.info("DiscoveryManager executing Google Places search for '%s' in '%s'", query, location)
            return self.google_service.search_places(
                query=f"{query} in {location}".strip() if location and location.lower() not in query.lower() else query,
                max_results=max_results,
                country=country
            )

        # 3. Automatic Mode: Google Places with OpenStreetMap fallback
        logger.info("DiscoveryManager executing in 'auto' mode (Google Places with OSM fallback)")

        # Full search string for Google Places
        full_query = f"{query} in {location}".strip() if location and location.lower() not in query.lower() else query

        # Try Google Places first
        google_records, g_calls, google_err = self.google_service.search_places(
            query=full_query,
            max_results=max_results,
            country=country
        )

        # If Google Places succeeded with records or genuine ZERO_RESULTS without error
        if google_records:
            return google_records, g_calls, None

        if google_err == "ZERO_RESULTS":
            logger.info("Google Places returned zero results. Attempting OpenStreetMap before concluding.")
            osm_records, osm_calls, osm_err = self.osm_service.search_places(
                query=query,
                location=location,
                area=area,
                country=country,
                max_results=max_results
            )
            total_calls = g_calls + osm_calls
            if osm_records:
                logger.info("OpenStreetMap found %d records after Google Places returned zero results.", len(osm_records))
                return osm_records, total_calls, None
            return [], total_calls, "ZERO_RESULTS"

        # Check if Google Places had a billing, quota, or configuration issue
        is_fallback_eligible = (
            not self.google_service.is_configured()
            or GooglePlacesService.is_billing_or_quota_error(google_err)
            or bool(google_err)
        )

        if is_fallback_eligible:
            err_category = GooglePlacesService.categorize_error(google_err)
            logger.warning(
                "Google Places discovery unavailable [%s: %s]. Automatically falling back to OpenStreetMap Overpass API.",
                err_category, google_err or "Key unconfigured"
            )

            osm_records, osm_calls, osm_err = self.osm_service.search_places(
                query=query,
                location=location,
                area=area,
                country=country,
                max_results=max_results
            )
            total_calls = g_calls + osm_calls

            if osm_records:
                logger.info("OpenStreetMap fallback successful: discovered %d records.", len(osm_records))
                return osm_records, total_calls, None

            # Both failed
            combined_error = (
                f"Google Places unavailable ({google_err or 'unconfigured key'}). "
                f"OpenStreetMap Overpass fallback error: ({osm_err or 'no records found'})."
            )
            logger.error("Both discovery providers failed: %s", combined_error)
            return [], total_calls, combined_error

        # Generic non-fallback failure
        return [], g_calls, google_err or "Unknown discovery error"


# Singleton instance
discovery_manager = DiscoveryManager()

