import datetime
from typing import Dict, Any, List, Tuple, Optional
from services.google_places_service import google_places_service
from services.discovery_manager import discovery_manager
from config.logging_config import logger


class BusinessDiscoveryAgent:
    """Agent 2: Executes business discovery queries using Google Places API and OpenStreetMap Overpass."""

    def __init__(self, places_service=None, discovery_mgr=None):
        self.places_service = places_service or google_places_service
        self.discovery_manager = discovery_mgr or discovery_manager

    def run(
        self,
        queries: List[str],
        max_results: int = 20,
        country: str = "India",
        provider: Optional[str] = None,
        city: str = "",
        area: str = ""
    ) -> Tuple[List[Dict[str, Any]], int, List[str]]:
        """
        Executes discovery queries, retrieves raw business listings.
        Supports provider routing and automatic fallback.
        Returns:
            (discovered_records, api_calls_count, errors_list)
        """
        all_records = []
        seen_place_ids = set()
        total_api_calls = 0
        errors = []

        for q in queries:
            if len(all_records) >= max_results:
                break

            remaining = max_results - len(all_records)
            results, calls, err = self.discovery_manager.discover_businesses(
                query=q,
                location=city,
                area=area,
                country=country,
                max_results=remaining,
                provider=provider
            )
            total_api_calls += calls
            if err:
                errors.append(err)

            for rec in results:
                p_id = rec.get("place_id")
                if p_id and p_id in seen_place_ids:
                    continue
                if p_id:
                    seen_place_ids.add(p_id)

                if "source" not in rec or not rec.get("source"):
                    rec["source"] = "Google Places API" if not rec.get("is_demo") else "Simulated Places Data (Demo Mode)"
                rec["retrieved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                all_records.append(rec)

                if len(all_records) >= max_results:
                    break

        logger.info("BusinessDiscoveryAgent discovered %d records across %d queries (API calls: %d)",
                    len(all_records), len(queries), total_api_calls)

        return all_records, total_api_calls, errors


business_discovery_agent = BusinessDiscoveryAgent()

