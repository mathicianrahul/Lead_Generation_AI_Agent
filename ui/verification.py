import streamlit as st
import datetime
from database.connection import SessionLocal
from database.repository import LeadRepository
from services.website_check_service import website_check_service


def render_verification():
    st.markdown('<div class="section-title">Website Verification Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Inspect verification evidence, analyze online presence, and manually verify website statuses.</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        repo = LeadRepository(db)

        tabs = st.tabs([
            "🔴 No Website Found",
            "🟣 Social Media Only",
            "🟡 Needs Verification / Failed",
            "🟢 Has Existing Website"
        ])

        def render_status_list(status_filter_list, tab_key):
            leads, count = repo.filter_leads(limit=100)
            filtered = [l for l in leads if l.website_status in status_filter_list]

            if not filtered:
                st.info("No businesses currently in this classification category.")
                return

            st.caption(f"Displaying **{len(filtered)}** businesses.")

            for lead in filtered:
                with st.expander(f"{lead.business_name} ({lead.category or 'Business'} — {lead.city or ''})"):
                    col_info, col_override = st.columns([3, 2])

                    with col_info:
                        st.markdown(f"**Current Status**: `{lead.website_status}` (Confidence: {int((lead.verification_confidence or 0.0)*100)}%)")
                        st.markdown(f"**Listed URL**: {lead.website_url or 'None listed'}")
                        st.markdown(f"**Address**: {lead.full_address or 'Not available'}")
                        if lead.maps_url:
                            st.markdown(f"[📍 Open Google Maps Listing]({lead.maps_url})")

                        # Display verification history
                        if lead.verification_results:
                            latest_v = lead.verification_results[-1]
                            st.markdown(f"**Evidence**: {latest_v.evidence_summary}")
                            st.markdown(f"**Method / Source**: {latest_v.verification_method} via {latest_v.source}")
                            st.caption(f"Checked at: {str(latest_v.checked_at)[:19]}")

                    with col_override:
                        st.markdown("##### Manual Status Correction")
                        new_status = st.selectbox(
                            "Correct Website Status",
                            ["NO_WEBSITE_FOUND", "SOCIAL_MEDIA_ONLY", "DIRECTORY_ONLY", "WEBSITE_FOUND", "UNVERIFIED"],
                            index=["NO_WEBSITE_FOUND", "SOCIAL_MEDIA_ONLY", "DIRECTORY_ONLY", "WEBSITE_FOUND", "UNVERIFIED"].index(lead.website_status) if lead.website_status in ["NO_WEBSITE_FOUND", "SOCIAL_MEDIA_ONLY", "DIRECTORY_ONLY", "WEBSITE_FOUND", "UNVERIFIED"] else 0,
                            key=f"corr_status_{lead.id}_{tab_key}"
                        )
                        corrected_url = st.text_input("Verified Website URL (if found)", value=lead.website_url or "", key=f"corr_url_{lead.id}_{tab_key}")
                        override_reason = st.text_input("Reason for manual correction", placeholder="e.g. Verified via official business sign", key=f"corr_reason_{lead.id}_{tab_key}")

                        if st.button("Apply Manual Verification", key=f"apply_corr_{lead.id}_{tab_key}", use_container_width=True):
                            repo.record_verification(
                                lead_id=lead.id,
                                method="MANUAL_USER_OVERRIDE",
                                status=new_status,
                                evidence=f"Manual override: {override_reason or 'User verified'}. Previous status was {lead.website_status}.",
                                source="Human Auditor",
                                confidence=1.0,
                                candidate_url=corrected_url.strip() if corrected_url.strip() else None
                            )
                            repo.update_lead(lead.id, {
                                "website_status": new_status,
                                "website_url": corrected_url.strip() if corrected_url.strip() else None,
                                "verification_confidence": 1.0
                            })
                            repo.log_audit(
                                event_type="WEBSITE_STATUS_OVERRIDE",
                                entity_type="lead",
                                entity_id=str(lead.id),
                                outcome="SUCCESS",
                                details=f"Changed status from {lead.website_status} to {new_status}"
                            )
                            st.success("Manual correction recorded with audit history!")
                            st.rerun()

        with tabs[0]:
            render_status_list(["NO_WEBSITE_FOUND"], "tab_no_web")

        with tabs[1]:
            render_status_list(["SOCIAL_MEDIA_ONLY", "DIRECTORY_ONLY"], "tab_social")

        with tabs[2]:
            render_status_list(["UNVERIFIED", "CHECK_FAILED"], "tab_unverified")

        with tabs[3]:
            render_status_list(["WEBSITE_FOUND", "WEBSITE_FOUND_ACCESSIBLE"], "tab_has_web")

    finally:
        db.close()

