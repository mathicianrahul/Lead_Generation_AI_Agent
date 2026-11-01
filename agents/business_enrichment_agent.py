import datetime
from typing import List, Dict, Any
from utils.email_validation import validate_email_address
from config.logging_config import logger


class BusinessEnrichmentAgent:
    """Agent 4: Enriches business contacts and validates email syntax."""

    def run(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched = []

        for rec in records:
            r = dict(rec)
            # Check existing email
            raw_email = r.get("email")
            if raw_email:
                is_valid, clean_email, _ = validate_email_address(raw_email)
                if is_valid:
                    r["email"] = clean_email
                    r["email_source"] = r.get("email_source") or "Google Place Listing"
                    r["email_validated_at"] = datetime.datetime.utcnow().isoformat()
                else:
                    r["email"] = None
                    r["email_source"] = None
            else:
                r["email"] = None
                r["email_source"] = None

            enriched.append(r)

        logger.info("BusinessEnrichmentAgent enriched %d records.", len(enriched))
        return enriched


business_enrichment_agent = BusinessEnrichmentAgent()

