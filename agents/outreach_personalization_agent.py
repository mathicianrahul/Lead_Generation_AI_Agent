from typing import List, Dict, Any, Optional
from services.llm_service import llm_service
from config.logging_config import logger


class OutreachPersonalizationAgent:
    """Agent 8: Prepares evidence-grounded personalized email drafts for qualified leads."""

    def __init__(self, llm=llm_service):
        self.llm = llm

    def run(self, leads: List[Dict[str, Any]], sender_name: str = "Web Solutions Team") -> List[Dict[str, Any]]:
        """
        Generates personalized email drafts for leads.
        Only generates drafts for leads with email available or notes manual phone approach.
        """
        drafts = []

        for lead in leads:
            b_name = lead.get("business_name", "Business Owner")
            cat = lead.get("category", "Local Business")
            city = lead.get("city", "")
            area = lead.get("area")
            rating = lead.get("rating")
            reviews = lead.get("review_count", 0)
            web_status = lead.get("website_status", "NO_WEBSITE_FOUND")
            recipient_email = lead.get("email")

            # Generate personalized content
            draft_content = self.llm.generate_personalized_draft(
                business_name=b_name,
                category=cat,
                city=city,
                area=area,
                rating=rating,
                review_count=reviews,
                website_status=web_status,
                sender_name=sender_name
            )

            draft_item = {
                "lead_id": lead.get("id"),
                "business_name": b_name,
                "recipient_email": recipient_email or "No public email listed",
                "email_source": lead.get("email_source") or "Google Place Listing",
                "has_email": bool(recipient_email),
                "subject": draft_content.subject,
                "body": draft_content.body,
                "proposed_features": draft_content.proposed_features,
                "rationale": draft_content.rationale,
                "personalization_evidence": draft_content.personalization_evidence,
                "status": "DRAFT_READY" if recipient_email else "EMAIL_UNAVAILABLE"
            }
            drafts.append(draft_item)

        logger.info("OutreachPersonalizationAgent generated %d email drafts.", len(drafts))
        return drafts


outreach_personalization_agent = OutreachPersonalizationAgent()

