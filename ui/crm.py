import streamlit as st
import pandas as pd
import datetime
from database.connection import SessionLocal
from database.repository import LeadRepository


def render_crm():
    st.markdown('<div class="section-title">Client Relationship Management (CRM)</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Track outreach pipelines, schedule client follow-ups, and manage website sales opportunities.</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        metrics = repo.get_metrics()

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Total Prospects in CRM", metrics['total_discovered'])
        with col_m2:
            st.metric("Interested Leads", metrics['interested'])
        with col_m3:
            st.metric("Converted Clients", metrics['converted'])
        with col_m4:
            st.metric("Pipeline Deal Value", f"₹{metrics['pipeline_value']:,.0f}")

        st.write("---")

        stage_filter = st.selectbox(
            "Filter by Opportunity Stage",
            ["All Stages", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Email sent", "Call planned", "Not contacted", "Not interested"],
            index=0
        )

        leads, total = repo.filter_leads(
            contact_status=stage_filter if stage_filter != "All Stages" else None,
            limit=100
        )

        if not leads:
            st.info("No leads currently in this CRM stage.")
            return

        for lead in leads:
            with st.expander(f"**{lead.business_name}** | Stage: **{lead.contact_status}** | Value: ₹{lead.estimated_deal_value or 0:,.0f} | Location: {lead.city or ''}"):
                c1, c2 = st.columns([3, 2])

                with c1:
                    st.markdown(f"**Contact**: Phone: `{lead.phone_number or 'N/A'}` | Email: `{lead.emails[0].email_address if lead.emails else 'N/A'}`")
                    st.markdown(f"**Category**: {lead.category} | **Address**: {lead.full_address or 'N/A'}")
                    if lead.notes:
                        st.info(f"**Notes**: {lead.notes}")

                    # Display contact history events
                    history = repo.get_lead_contact_history(lead.id)
                    if history:
                        st.markdown("###### Interaction Timeline")
                        for h in history[:3]:
                            st.caption(f"• **{h.event_type}** ({h.contact_method}) on {str(h.event_timestamp)[:16]}: {h.notes or ''}")

                with c2:
                    st.markdown("###### Update Opportunity")
                    new_stage = st.selectbox(
                        "Stage",
                        ["Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"],
                        index=["Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"].index(lead.contact_status) if lead.contact_status in ["Not contacted", "Email drafted", "Email sent", "Call planned", "Interested", "Meeting scheduled", "Proposal sent", "Converted", "Not interested", "Opted out", "Do not contact"] else 0,
                        key=f"crm_stage_{lead.id}"
                    )
                    deal_val = st.number_input("Estimated Value (₹)", value=float(lead.estimated_deal_value or 0.0), key=f"crm_val_{lead.id}", step=5000.0)
                    new_notes = st.text_area("Add Interaction Note", key=f"crm_note_{lead.id}", height=65)

                    if st.button("Update CRM Record", key=f"crm_upd_btn_{lead.id}", use_container_width=True):
                        repo.update_lead(lead.id, {
                            "contact_status": new_stage,
                            "estimated_deal_value": deal_val,
                            "notes": f"{lead.notes}\n[{datetime.datetime.now().strftime('%Y-%m-%d')}]: {new_notes}" if lead.notes and new_notes else (new_notes or lead.notes)
                        })
                        if new_notes or new_stage != lead.contact_status:
                            repo.log_contact_event(
                                lead_id=lead.id,
                                contact_method="CRM Direct Update",
                                event_type=new_stage,
                                notes=new_notes
                            )
                        st.success("Opportunity updated successfully!")
                        st.rerun()

    finally:
        db.close()

