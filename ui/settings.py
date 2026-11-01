import os
import streamlit as st
from config.settings import settings
from services.google_places_service import google_places_service
from services.gmail_service import gmail_service
from database.connection import SessionLocal, init_db
from database.models import Lead, SearchJob, EmailDraft, VerificationResult, ContactHistory


def render_settings():
    st.markdown('<div class="section-title">System Settings & Integrations</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Manage API connections, configure lead scoring weights, and monitor operational safeguards.</div>', unsafe_allow_html=True)

    # Section 1: Integration Status Overview
    st.markdown("### Integration Status")
    c_int1, c_int2, c_int3 = st.columns(3)

    with c_int1:
        places_ok = google_places_service.is_configured()
        st.markdown(f"""
        <div style="padding: 14px; border: 1px solid {'#86EFAC' if places_ok else '#FCA5A5'}; border-radius: 8px; background-color: {'#F0FDF4' if places_ok else '#FEF2F2'};">
            <h4 style="margin: 0; color: {'#15803D' if places_ok else '#B91C1C'};">Google Places API</h4>
            <p style="margin: 4px 0 0 0; font-size: 0.85rem;">Status: <b>{'🟢 Live Connected' if places_ok else '🟡 Missing Key (Demo Mode Active)'}</b></p>
        </div>
        """, unsafe_allow_html=True)

    with c_int2:
        llm_ok = settings.has_llm_key()
        st.markdown(f"""
        <div style="padding: 14px; border: 1px solid {'#86EFAC' if llm_ok else '#93C5FD'}; border-radius: 8px; background-color: {'#F0FDF4' if llm_ok else '#EFF6FF'};">
            <h4 style="margin: 0; color: {'#15803D' if llm_ok else '#1D4ED8'};">AI Model Provider</h4>
            <p style="margin: 4px 0 0 0; font-size: 0.85rem;">Status: <b>{'🟢 ' + settings.llm_provider.title() if llm_ok else '🔵 Built-in Deterministic Engine'}</b></p>
        </div>
        """, unsafe_allow_html=True)

    with c_int3:
        gmail_ok = gmail_service.is_authenticated()
        st.markdown(f"""
        <div style="padding: 14px; border: 1px solid {'#86EFAC' if gmail_ok else '#FDE047'}; border-radius: 8px; background-color: {'#F0FDF4' if gmail_ok else '#FEFCE8'};">
            <h4 style="margin: 0; color: {'#15803D' if gmail_ok else '#854D0E'};">Gmail OAuth 2.0</h4>
            <p style="margin: 4px 0 0 0; font-size: 0.85rem;">Status: <b>{'🟢 OAuth Authenticated' if gmail_ok else '🟡 Simulation Mode (Safe)'}</b></p>
        </div>
        """, unsafe_allow_html=True)

    st.write("---")

    # Section 2: Credential Configuration Guide
    with st.expander("🔑 How to Configure External Credentials", expanded=False):
        st.markdown("""
        LeadPilot AI functions out-of-the-box in demo mode, but for live deployment, configure your environment variables in `.env`:

        1. **Google Places API Key**:
           - Visit [Google Cloud Console](https://console.cloud.google.com/).
           - Enable **Places API (New)**.
           - Create an API key with API restrictions limited to Places API.
           - Add to `.env`: `GOOGLE_MAPS_API_KEY=AIzaSy...`

        2. **Hugging Face / LLM Token (Optional)**:
           - Visit [Hugging Face Settings -> Tokens](https://huggingface.co/settings/tokens).
           - Create a read token.
           - Add to `.env`: `HUGGINGFACE_API_TOKEN=hf_...`
           - *Note: If omitted, LeadPilot's high-performance built-in deterministic personalization engine is used.*

        3. **Gmail OAuth 2.0 (Optional for Sending)**:
           - In Google Cloud Console, enable **Gmail API**.
           - Configure OAuth Consent Screen and create OAuth 2.0 Client ID (Desktop Application).
           - Download client secrets as `credentials.json` into the project root.
           - All emails require explicit human approval before dispatch.
        """)

    # Section 3: Lead Scoring Weight Adjuster
    st.markdown("### Configurable Lead Scoring Weights (Total 100 Points)")
    st.caption("Customize the relative importance of prospect signals to match your web sales criteria.")

    with st.form("scoring_weights_form"):
        col_w1, col_w2 = st.columns(2)
        with col_w1:
            w_web = st.slider("Website Opportunity (No Website Found)", min_value=20, max_value=60, value=int(settings.scoring_weights.website_opportunity))
            w_phone = st.slider("Public Business Phone Available", min_value=5, max_value=30, value=int(settings.scoring_weights.phone_available))
            w_email = st.slider("Public Business Email Available", min_value=5, max_value=30, value=int(settings.scoring_weights.email_available))
        with col_w2:
            w_ops = st.slider("Active Business Operations Evidence", min_value=5, max_value=30, value=int(settings.scoring_weights.active_operations))
            w_val = st.slider("Potential Website Value for Category", min_value=5, max_value=30, value=int(settings.scoring_weights.category_website_value))

        total_weight = w_web + w_phone + w_email + w_ops + w_val
        st.markdown(f"**Total Weight Sum**: `{total_weight} / 100` {'✅ Balanced' if total_weight == 100 else '⚠️ (Adjust to sum to 100)'}")

        if st.form_submit_button("💾 Save Scoring Weights"):
            settings.scoring_weights.website_opportunity = float(w_web)
            settings.scoring_weights.phone_available = float(w_phone)
            settings.scoring_weights.email_available = float(w_email)
            settings.scoring_weights.active_operations = float(w_ops)
            settings.scoring_weights.category_website_value = float(w_val)
            st.success("Scoring weights updated for all future lead evaluations!")

    st.write("---")

    # Section 4: Safety Safeguards and Limits
    st.markdown("### Safety Controls & Rate Limits")
    col_lim1, col_lim2, col_lim3 = st.columns(3)
    with col_lim1:
        st.number_input("Daily Email Dispatch Cap", value=settings.max_daily_emails, disabled=True, help="Set MAX_DAILY_EMAILS in .env to modify")
    with col_lim2:
        st.number_input("Max Search Discovery Limit", value=settings.max_search_results, disabled=True)
    with col_lim3:
        st.number_input("HTTP Verification Timeout (Seconds)", value=settings.http_timeout_seconds, disabled=True)

    st.write("---")

    # Section 5: Database Maintenance
    st.markdown("### Database & Data Maintenance")
    st.caption(f"Connected Database URL: `{settings.database_url}`")

    if st.button("🗑️ Clear Demo Data (Keep Schema Clean)", type="secondary"):
        db = SessionLocal()
        try:
            demo_leads = db.query(Lead).filter(Lead.is_demo == True).all()
            for l in demo_leads:
                db.delete(l)
            db.commit()
            st.success(f"Cleared {len(demo_leads)} demo records. Real API data remains preserved.")
            st.rerun()
        finally:
            db.close()

