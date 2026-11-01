from typing import List, Dict, Any
from services.website_check_service import website_check_service
from services.web_search_service import web_search_service
from config.logging_config import logger


class WebsiteVerificationAgent:
    """Agent 3: Transparent, multi-stage website verification pipeline."""

    def __init__(self, check_service=website_check_service, search_service=web_search_service):
        self.check_service = check_service
        self.search_service = search_service

    def run(self, records: List[Dict[str, Any]], enable_deep_search: bool = False) -> List[Dict[str, Any]]:
        """
        Verifies each record's website status.
        Adds `website_status`, `verification_confidence`, `verification_evidence`.
        """
        verified_records = []

        for rec in records:
            raw_url = rec.get("website_url")
            b_name = rec.get("business_name", "")
            city = rec.get("city", "")
            category = rec.get("category", "")
            source = rec.get("source", "")

            # If no website listed and deep search is enabled, attempt Stage C check
            if not raw_url and enable_deep_search:
                found_url = self.search_service.search_business_website(b_name, city, category)
                if found_url:
                    raw_url = found_url

            # For OpenStreetMap records where website is missing:
            # Do not assume that a missing website tag means the business definitely has no website.
            if not raw_url and "openstreetmap" in str(source).lower():
                rec_copy = dict(rec)
                rec_copy["website_status"] = "UNVERIFIED"
                rec_copy["verification_confidence"] = 0.50
                rec_copy["verification_evidence"] = (
                    "No website tag present in OpenStreetMap record. "
                    "Crowdsourced map data may omit website tags; business website presence is unverified."
                )
                verified_records.append(rec_copy)
                continue

            # Execute verification
            result = self.check_service.verify_website(raw_url, b_name)

            rec_copy = dict(rec)
            rec_copy["website_status"] = result["status"]
            rec_copy["verification_confidence"] = result["confidence"]
            rec_copy["verification_evidence"] = result["evidence"]
            if result.get("candidate_url"):
                rec_copy["website_url"] = result["candidate_url"]

            verified_records.append(rec_copy)

        logger.info("WebsiteVerificationAgent verified %d businesses.", len(verified_records))
        return verified_records


website_verification_agent = WebsiteVerificationAgent()

