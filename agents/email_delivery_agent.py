from typing import Dict, Any, Tuple, Optional
from services.gmail_service import gmail_service
from config.logging_config import logger


class EmailDeliveryAgent:
    """Agent 9: Manages approved email delivery with strict human gatekeeping and safety controls."""

    def __init__(self, delivery_service=gmail_service):
        self.delivery_service = delivery_service

    def run(
        self,
        draft: Dict[str, Any],
        is_human_approved: bool,
        is_suppressed: bool,
        today_sent_count: int
    ) -> Tuple[bool, Optional[str], str]:
        """
        Executes delivery for a single draft.
        Returns:
            (success, message_id, status_message)
        """
        recipient = draft.get("recipient_email")
        subject = draft.get("subject")
        body = draft.get("body")

        # 1. Human approval check
        if not is_human_approved:
            logger.warning("Delivery blocked for %s: Human approval not granted.", recipient)
            return False, None, "APPROVAL_REQUIRED: Email was not approved for sending."

        # 2. Suppression check
        if is_suppressed:
            logger.warning("Delivery blocked for %s: Recipient is in suppression list.", recipient)
            return False, None, "SUPPRESSED: Recipient is on suppression list (Opted Out / Do Not Contact)."

        # 3. Check email presence
        if not recipient or "@" not in recipient:
            return False, None, "INVALID_RECIPIENT: No valid public email available."

        # 4. Dispatch via Gmail Service
        success, msg_id, status_msg = self.delivery_service.send_approved_email(
            recipient_email=recipient,
            subject=subject,
            body=body,
            is_human_approved=is_human_approved,
            today_sent_count=today_sent_count
        )

        logger.info("EmailDeliveryAgent result for %s: %s (Msg ID: %s)", recipient, status_msg, msg_id)
        return success, msg_id, status_msg


email_delivery_agent = EmailDeliveryAgent()

