import streamlit as st
import datetime
from database.connection import SessionLocal
from database.repository import LeadRepository
from agents.email_delivery_agent import email_delivery_agent
from services.gmail_service import gmail_service
from config.settings import settings


def render_outreach():
    st.markdown('<div class="section-title">Email Outreach & Human Approval Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Review, edit, approve, and safely dispatch personalized website proposals. No email is ever sent without explicit human authorization.</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        repo = LeadRepository(db)

        # Calculate today's sent count
        drafts_all = repo.list_drafts()
        today_date = datetime.date.today()
        today_sent = len([
            d for d in drafts_all if d.status == "SENT" and d.sent_at and d.sent_at.date() == today_date
        ])

        # Status Banner
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Daily Sending Cap", f"{today_sent} / {settings.max_daily_emails} sent")
        with col_stat2:
            pending_count = len([d for d in drafts_all if d.status in ("DRAFT_READY", "PENDING_APPROVAL")])
            st.metric("Pending Approval", pending_count)
        with col_stat3:
            gmail_conn = "Connected (OAuth 2.0)" if gmail_service.is_authenticated() else "Simulation / Test Mode"
            st.metric("Gmail Delivery Mode", gmail_conn)

        st.write("---")

        status_filter = st.selectbox(
            "Filter Outreach Status",
            ["All", "DRAFT_READY", "PENDING_APPROVAL", "APPROVED", "SENT", "SEND_FAILED", "OPTED_OUT", "DO_NOT_CONTACT"],
            index=0
        )

        filtered_drafts = repo.list_drafts(status=status_filter)

        if not filtered_drafts:
            st.info("No email drafts in this view. When you run searches on prospects with public emails, drafts will appear here.")
            return

        for draft in filtered_drafts:
            lead = draft.lead
            b_name = lead.business_name if lead else "Unknown Business"
            is_suppressed = repo.is_suppressed(draft.recipient_email, "email")

            status_badge = {
                "DRAFT_READY": "🟡 Ready for Review",
                "PENDING_APPROVAL": "🟠 Pending Approval",
                "APPROVED": "🟢 Approved to Send",
                "SENT": "✅ Sent",
                "SEND_FAILED": "❌ Failed",
                "OPTED_OUT": "⛔ Opted Out",
                "DO_NOT_CONTACT": "🚫 Suppressed"
            }.get(draft.status, draft.status)

            with st.expander(f"**{b_name}** | To: `{draft.recipient_email}` | {status_badge}", expanded=(draft.status in ["DRAFT_READY", "PENDING_APPROVAL"])):
                if is_suppressed:
                    st.error("⚠️ **Suppression Notice**: This recipient or domain is listed on your Do-Not-Contact list. Sending is locked.")

                col_meta1, col_meta2 = st.columns([3, 1])
                with col_meta1:
                    st.caption(f"**Personalization Grounding**: {draft.personalization_evidence or 'Category and location tailored proposal'}")
                    if draft.sent_at:
                        st.caption(f"Dispatched at: {str(draft.sent_at)[:19]} (Provider ID: `{draft.provider_message_id}`)")

                with col_meta2:
                    st.caption(f"Last updated: {str(draft.updated_at)[:19] if draft.updated_at else 'N/A'}")

                # Editable Subject & Body
                subj_input = st.text_input("Subject Line", value=draft.subject, key=f"subj_{draft.id}")
                body_input = st.text_area("Message Body", value=draft.body, height=220, key=f"body_{draft.id}")

                col_a1, col_a2, col_a3, col_a4 = st.columns(4)

                with col_a1:
                    if st.button("💾 Save Edits", key=f"save_draft_{draft.id}", use_container_width=True):
                        repo.create_or_update_draft(
                            lead_id=draft.lead_id,
                            recipient_email=draft.recipient_email,
                            subject=subj_input,
                            body=body_input,
                            personalization_evidence=draft.personalization_evidence
                        )
                        st.success("Draft saved!")
                        st.rerun()

                with col_a2:
                    if draft.status in ("DRAFT_READY", "PENDING_APPROVAL"):
                        if st.button("✅ Approve for Sending", key=f"appr_{draft.id}", use_container_width=True):
                            repo.update_draft_status(draft.id, "APPROVED")
                            repo.log_audit("EMAIL_APPROVED", "email_draft", str(draft.id), "SUCCESS", f"User approved draft for {draft.recipient_email}")
                            st.success("Draft approved!")
                            st.rerun()
                    elif draft.status == "APPROVED":
                        st.caption("Status: Approved")

                with col_a3:
                    # Explicit Send button with strict safety gate
                    can_send = (draft.status == "APPROVED") and not is_suppressed and (today_sent < settings.max_daily_emails)
                    send_btn = st.button(
                        "🚀 Send Email Now",
                        key=f"send_{draft.id}",
                        disabled=not can_send,
                        type="primary" if can_send else "secondary",
                        use_container_width=True,
                        help="Requires approval first and respects suppression + daily limit."
                    )
                    if send_btn:
                        draft_dict = {
                            "recipient_email": draft.recipient_email,
                            "subject": subj_input,
                            "body": body_input
                        }
                        success, msg_id, status_msg = email_delivery_agent.run(
                            draft=draft_dict,
                            is_human_approved=True,
                            is_suppressed=is_suppressed,
                            today_sent_count=today_sent
                        )
                        if success:
                            repo.update_draft_status(draft.id, "SENT", provider_id=msg_id)
                            repo.log_contact_event(
                                lead_id=draft.lead_id,
                                contact_method="Gmail Outreach",
                                event_type="Email sent",
                                notes=f"Sent proposal: '{subj_input}'"
                            )
                            repo.log_audit("EMAIL_SENT", "email_draft", str(draft.id), "SUCCESS", f"Sent to {draft.recipient_email}")
                            st.success(f"Dispatched: {status_msg}")
                            st.rerun()
                        else:
                            repo.update_draft_status(draft.id, "SEND_FAILED", error_message=status_msg)
                            st.error(f"Send failed: {status_msg}")

                with col_a4:
                    if st.button("🚫 Add to Suppression", key=f"supp_{draft.id}", use_container_width=True):
                        repo.add_suppression(draft.recipient_email, "email", "User added from outreach hub", "MANUAL")
                        repo.update_draft_status(draft.id, "DO_NOT_CONTACT")
                        st.warning(f"Suppressed {draft.recipient_email}")
                        st.rerun()

    finally:
        db.close()

