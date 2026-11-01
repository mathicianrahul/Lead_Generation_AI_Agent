import datetime
from typing import Dict, Any, Optional
from config.logging_config import logger


class CRMAgent:
    """Agent 10: Relationship tracking, follow-up scheduling, and conversion status management."""

    VALID_STATUSES = [
        "Not contacted", "Email drafted", "Email sent", "Call planned",
        "Interested", "Meeting scheduled", "Proposal sent", "Converted",
        "Not interested", "Opted out", "Do not contact"
    ]

    def update_lead_crm(
        self,
        lead_id: int,
        status: str,
        notes: Optional[str] = None,
        next_action: Optional[str] = None,
        next_action_date: Optional[datetime.datetime] = None,
        deal_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """Validates and packages CRM update data."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid contact status: '{status}'. Must be one of {self.VALID_STATUSES}")

        update_payload = {
            "lead_id": lead_id,
            "contact_status": status,
            "notes": notes,
            "next_action": next_action,
            "next_action_date": next_action_date,
            "estimated_deal_value": deal_value,
            "updated_at": datetime.datetime.utcnow()
        }

        logger.info("CRMAgent updated lead %d status to '%s'", lead_id, status)
        return update_payload


crm_agent = CRMAgent()

