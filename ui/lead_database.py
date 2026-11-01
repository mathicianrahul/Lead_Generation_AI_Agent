import streamlit as st
import pandas as pd
from typing import Dict, Any

from database.connection import SessionLocal
from database.repository import LeadRepository
from services.website_check_service import website_check_service
from services.llm_service import llm_service


def render_lead_database():
    st.markdown('<div class="section-title">Lead Database</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Search, filter, inspect, and qualify discovered business prospects.</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        repo = LeadRepository(db)

        # Filters Row
        with st.expander("🔍 Search & Filter Controls", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                search_query = st.text_input("Search Business Name, Address, or Phone", placeholder="Type keyword...")
                city_filter = st.text_input("Filter by City", placeholder="e.g. Bengaluru, Mumbai")
            with f2:
                web_status_filter = st.selectbox(
                    "Website Status",
                    ["All", "NO_WEBSITE_FOUND", "SOCIAL_MEDIA_ONLY", "DIRECTORY_ONLY", "WEBSITE_FOUND", "UNVERIFIED", "CHECK_FAILED"],
                    index=0
                )
                priority_filter = st.selectbox("Priority Band", ["All", "High", "Medium", "Low"], index=0)
            with f3:
                contact_filter = st.selectbox(
                    "CRM Contact Status",
                    ["All", "Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"],
                    index=0
                )
                min_score = st.slider("Min Lead Score", 0, 100, 0, 5)
            with f4:
                has_phone = st.checkbox("Has Phone Number", value=False)
                has_email = st.checkbox("Has Email Address", value=False)
                page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)

        # Query Leads from DB
        leads, total_count = repo.filter_leads(
            city=city_filter.strip() if city_filter.strip() else None,
            website_status=web_status_filter if web_status_filter != "All" else None,
            priority=priority_filter if priority_filter != "All" else None,
            contact_status=contact_filter if contact_filter != "All" else None,
            min_score=float(min_score) if min_score > 0 else None,
            has_phone=True if has_phone else None,
            has_email=True if has_email else None,
            search_query=search_query.strip() if search_query.strip() else None,
            limit=page_size,
            offset=0
        )

        st.caption(f"Showing **{len(leads)}** of **{total_count}** matching leads.")

        if not leads:
            st.info("No leads found matching current criteria. Try adjusting your filters or run a new search.")
            return

        # Render Leads
        for lead in leads:
            # Color-coded badge for website status
            web_badge = ""
            if lead.website_status == "NO_WEBSITE_FOUND":
                web_badge = "🔴 No Website Found"
            elif lead.website_status == "SOCIAL_MEDIA_ONLY":
                web_badge = "🟣 Social Media Only"
            elif lead.website_status == "WEBSITE_FOUND":
                web_badge = "🟢 Has Website"
            else:
                web_badge = f"🟡 {lead.website_status}"

            # Demo badge if simulated
            demo_tag = " [DEMO RECORD]" if lead.is_demo else ""

            exp_label = f"**{lead.business_name}** | {lead.category or 'Business'} — {lead.city or ''} | Score: **{lead.lead_score:.0f}** ({lead.priority}) | {web_badge}{demo_tag}"

            with st.expander(exp_label, expanded=False):
                col_left, col_right = st.columns([3, 2])

                with col_left:
                    st.markdown(f"**Business Name**: {lead.business_name}")
                    st.markdown(f"**Category**: {lead.category} | **Location**: {lead.area or ''}, {lead.city or ''}, {lead.state or ''}")
                    st.markdown(f"**Full Address**: {lead.full_address or 'Not available'}")
                    st.markdown(f"**Phone**: `{lead.phone_number or 'No phone listed'}`")
                    
                    # Email info
                    email_str = lead.emails[0].email_address if lead.emails else "No public email available"
                    st.markdown(f"**Public Email**: `{email_str}`")

                    # Website & Maps links
                    col_links = st.columns(2)
                    with col_links[0]:
                        if lead.maps_url:
                            st.markdown(f"[📍 Open Google Maps Listing]({lead.maps_url})")
                        else:
                            st.caption("No Maps URL available")
                    with col_links[1]:
                        if lead.website_url:
                            st.markdown(f"[🌐 Visit Listed URL]({lead.website_url})")
                        else:
                            st.caption("No website listed")

                    st.markdown(f"**Customer Reviews**: {lead.review_count} ratings ({lead.rating or 0.0}★)")
                    st.info(f"**Scoring Breakdown**: {lead.scoring_explanation}")

                with col_right:
                    st.markdown("##### CRM & Outreach Actions")
                    new_status = st.selectbox(
                        "Update CRM Status",
                        ["Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"],
                        index=["Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"].index(lead.contact_status) if lead.contact_status in ["Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"] else 0,
                        key=f"status_select_{lead.id}"
                    )

                    notes = st.text_area("Notes", value=lead.notes or "", key=f"notes_{lead.id}", height=70)
                    deal_val = st.number_input("Estimated Deal Value (₹)", value=float(lead.estimated_deal_value or 0.0), key=f"deal_{lead.id}", step=5000.0)

                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Save CRM Update", key=f"save_btn_{lead.id}", use_container_width=True):
                            repo.update_lead(lead.id, {
                                "contact_status": new_status,
                                "notes": notes,
                                "estimated_deal_value": deal_val
                            })
                            repo.log_contact_event(
                                lead_id=lead.id,
                                contact_method="CRM Update",
                                event_type=new_status,
                                notes=notes
                            )
                            st.success("Lead updated!")
                            st.rerun()

                    with col_btn2:
                        if st.button("🚫 Mark Do Not Contact", key=f"dnc_btn_{lead.id}", use_container_width=True):
                            repo.update_lead(lead.id, {"contact_status": "Do not contact"})
                            if lead.phone_number:
                                repo.add_suppression(lead.phone_number, "phone", "User marked Do Not Contact", "MANUAL")
                            if lead.emails:
                                repo.add_suppression(lead.emails[0].email_address, "email", "User marked Do Not Contact", "MANUAL")
                            st.warning("Lead added to suppression list.")
                            st.rerun()

                    # Re-verify button
                    if st.button("🔄 Re-Verify Website Status", key=f"reverif_{lead.id}", use_container_width=True):
                        res = website_check_service.verify_website(lead.website_url, lead.business_name)
                        repo.record_verification(
                            lead_id=lead.id,
                            method="MANUAL_TRIGGER",
                            status=res["status"],
                            evidence=res["evidence"],
                            source="HTTP Verification Probe",
                            confidence=res["confidence"],
                            candidate_url=res.get("candidate_url")
                        )
                        st.info(f"Verification Result: {res['status']} — {res['evidence']}")
                        st.rerun()

    finally:
        db.close()

