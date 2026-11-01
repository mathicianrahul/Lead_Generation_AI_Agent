import datetime
from typing import Dict, Any, List, Tuple
from services.google_places_service import google_places_service
from config.logging_config import logger


class BusinessDiscoveryAgent:
    """Agent 2: Executes business discovery queries using the official Google Places API."""

    def __init__(self, places_service=google_places_service):
        self.places_service = places_service

    def run(
        self,
        queries: List[str],
        max_results: int = 20,
        country: str = "India"
    ) -> Tuple[List[Dict[str, Any]], int, List[str]]:
        """
        Executes discovery queries, retrieves raw business listings.
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
            results, calls, err = self.places_service.search_places(
                query=q,
                max_results=remaining,
                country=country
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

                rec["source"] = "Google Places API" if not rec.get("is_demo") else "Simulated Places Data (Demo Mode)"
                rec["retrieved_at"] = datetime.datetime.utcnow().isoformat()
                all_records.append(rec)

                if len(all_records) >= max_results:
                    break

        logger.info("BusinessDiscoveryAgent discovered %d records across %d queries (API calls: %d)",
                    len(all_records), len(queries), total_api_calls)

        return all_records, total_api_calls, errors


business_discovery_agent = BusinessDiscoveryAgent()

