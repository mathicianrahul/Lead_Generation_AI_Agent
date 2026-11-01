import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="LeadPilot AI — Website Sales & Lead Generation",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

from config.settings import settings
from config.logging_config import logger
from database.connection import init_db, SessionLocal
from database.repository import LeadRepository
from ui.styles import CUSTOM_CSS
from ui.overview import render_overview
from ui.find_leads import render_find_leads
from ui.lead_database import render_lead_database
from ui.verification import render_verification
from ui.outreach import render_outreach
from ui.crm import render_crm
from ui.reports import render_reports
from ui.settings import render_settings

# Initialize Database Schema
init_db()

# Inject Custom Styling
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main():
    # ----------------- SIDEBAR -----------------
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 10px 0 16px 0;">
            <h2 style="color: #1E3A8A; margin: 0; font-weight: 800; font-size: 1.6rem; letter-spacing: -0.02em;">🧭 LeadPilot AI</h2>
            <p style="color: #64748B; font-size: 0.8rem; margin-top: 4px; font-weight: 500;">AI Lead Generation & Web Sales</p>
        </div>
        """, unsafe_allow_html=True)

        # Navigation Options
        page = st.radio(
            "Navigation",
            [
                "📊 Overview",
                "🔍 Find Leads",
                "📁 Lead Database",
                "🛡️ Website Verification",
                "✉️ Email Outreach",
                "💼 CRM & Pipeline",
                "📑 Reports & Export",
                "⚙️ Settings & Keys"
            ],
            index=0,
            label_visibility="collapsed"
        )

        st.markdown("---")

        # Sidebar Live Diagnostics
        db = SessionLocal()
        try:
            repo = LeadRepository(db)
            metrics = repo.get_metrics()
        finally:
            db.close()

        st.markdown("###### System Status")
        st.markdown(f"• Total Prospects: **{metrics['total_discovered']}**")
        st.markdown(f"• No Website Found: **{metrics['no_website_found']}**")
        st.markdown(f"• High Priority: **{metrics['high_priority']}**")
        st.markdown(f"• Pending Approval: **{metrics['pending_approval']}**")

        st.write("")
        has_places = settings.has_google_maps_key()
        if has_places:
            st.success("🟢 Google Places API: Connected")
        else:
            st.info("🟡 Mode: Demo / Simulated Data")

        st.caption("LeadPilot AI v1.0.0 • Production Ready")

    # ----------------- PAGE ROUTING -----------------
    if page == "📊 Overview":
        render_overview()
    elif page == "🔍 Find Leads":
        render_find_leads()
    elif page == "📁 Lead Database":
        render_lead_database()
    elif page == "🛡️ Website Verification":
        render_verification()
    elif page == "✉️ Email Outreach":
        render_outreach()
    elif page == "💼 CRM & Pipeline":
        render_crm()
    elif page == "📑 Reports & Export":
        render_reports()
    elif page == "⚙️ Settings & Keys":
        render_settings()


if __name__ == "__main__":
    main()

