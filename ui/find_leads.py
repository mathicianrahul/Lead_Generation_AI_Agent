import streamlit as st
import time

from config.settings import settings
from graph.workflow import run_lead_workflow
from agents.search_planning_agent import search_planning_agent, SearchPlanInput


def render_find_leads():
    st.markdown('<div class="section-title">Discover Target Businesses</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Configure search parameters to discover businesses, verify website status, and qualify leads.</div>', unsafe_allow_html=True)

    # API Key Notice / Demo Mode Indicator
    has_key = settings.has_google_maps_key()
    if not has_key:
        st.warning(
            "⚠️ **Google Places API Key Not Configured**: Running in **Demo Mode**. "
            "LeadPilot AI will generate realistically modeled, clearly labeled test data so you can test all verification, scoring, CRM, and export workflows without incurring API costs. "
            "To connect live Google Maps discovery, add `GOOGLE_MAPS_API_KEY` in Settings or your `.env` file."
        )

    with st.form("search_config_form"):
        col_loc1, col_loc2, col_loc3, col_loc4 = st.columns(4)
        with col_loc1:
            country = st.selectbox("Country", ["India", "United States", "United Kingdom", "Canada", "Australia", "UAE"], index=0)
        with col_loc2:
            state = st.text_input("State / Region", value="Karnataka" if country == "India" else "")
        with col_loc3:
            city = st.text_input("City *", value="Bengaluru")
        with col_loc4:
            area = st.text_input("Area / Neighborhood", value="Indiranagar", help="e.g. Indiranagar, Koramangala, Bandra West, Connaught Place")

        col_cat1, col_cat2 = st.columns([2, 2])
        with col_cat1:
            category = st.selectbox(
                "Business Category *",
                [
                    "Dental Clinic & Healthcare",
                    "Beauty Salon & Spa",
                    "Restaurant & Cafe",
                    "Gym & Fitness Studio",
                    "Hotel & Guest House",
                    "Coaching Institute & Academy",
                    "Automobile Repair & Service",
                    "Real Estate Agency",
                    "Travel & Tour Agency",
                    "Retail Store & Boutique",
                    "Interior Designer & Architect",
                    "Local Professional Services"
                ],
                index=0
            )
        with col_cat2:
            keywords = st.text_input("Custom Keywords (Optional)", placeholder="e.g. pediatric dental, sourdough bakery, crossfit")

        st.markdown("##### Advanced Filters & Agent Controls")
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            max_results = st.slider("Maximum Results Requested", min_value=5, max_value=60, value=15, step=5)
            min_score = st.slider("Minimum Lead Score to Qualify", min_value=0, max_value=90, value=50, step=5)
        with col_ctrl2:
            require_phone = st.checkbox("Require Valid Public Phone Number", value=True)
            require_email = st.checkbox("Require Valid Public Email Address", value=False)
            budget_limit = st.number_input("Max Search API Operations Limit", min_value=5, max_value=200, value=40)
        with col_ctrl3:
            enable_verification = st.checkbox("Enable Safe HTTP Website Verification", value=True, help="Performs safe HTTP check with SSRF protections")
            enable_ai_personalization = st.checkbox("Enable AI Outreach Personalization", value=True, help="Generates tailored email proposals using verified business facts")

        c_submit1, c_submit2 = st.columns([1, 4])
        with c_submit1:
            estimate_clicked = st.form_submit_button("📊 Estimate API Usage", use_container_width=True)
        with c_submit2:
            start_clicked = st.form_submit_button("🚀 Start Lead Discovery & Qualification", type="primary", use_container_width=True)

    # 1. Estimation Handling
    if estimate_clicked:
        plan_in = SearchPlanInput(
            country=country,
            state=state,
            city=city,
            area=area,
            category=category,
            keywords=keywords,
            max_results=max_results,
            min_score=min_score,
            budget_limit=budget_limit
        )
        plan_out = search_planning_agent.run(plan_in)
        st.info(f"**API Usage Estimate**: ~{plan_out.estimated_api_calls} Places API operations planned. Queries to execute: {', '.join(plan_out.queries)}")

    # 2. Search Execution Handling
    if start_clicked:
        if not city.strip():
            st.error("Please specify a city to search.")
            return

        st.write("---")
        st.markdown("### Agent Execution in Progress")

        progress_bar = st.progress(0)
        status_box = st.empty()
        agent_step_box = st.empty()

        def update_progress(step_name: str, pct: int, msg: str):
            progress_bar.progress(pct)
            status_box.markdown(f"**Current Phase**: {msg}")

        search_payload = {
            "country": country,
            "state": state,
            "city": city,
            "area": area,
            "category": category,
            "keywords": keywords,
            "max_results": max_results,
            "min_score": min_score,
            "require_phone": require_phone,
            "require_email": require_email,
            "enable_verification": enable_verification,
            "enable_ai_personalization": enable_ai_personalization,
            "budget_limit": budget_limit
        }

        with st.spinner("Multi-Agent Workflow executing..."):
            final_state = run_lead_workflow(search_payload, progress_callback=update_progress)

        progress_bar.progress(100)
        status_box.success("🎉 Search job completed successfully!")

        discovered_count = len(final_state.get("discovered_records", []))
        persisted_count = len(final_state.get("persisted_leads", []))
        qualified_count = len(final_state.get("qualified_leads", []))
        report_path = final_state.get("excel_report_path")

        st.markdown(f"""
        <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; margin-top: 12px;">
            <h4 style="color: #0F172A; margin-top: 0;">Execution Summary (Job: {final_state.get('job_id')})</h4>
            <ul>
                <li>Discovered: <b>{discovered_count}</b> listings</li>
                <li>Deduplicated & Persisted: <b>{persisted_count}</b> unique businesses</li>
                <li>Qualified Leads (Score >= {min_score}): <b>{qualified_count}</b></li>
                <li>API Operations: <b>{final_state.get('api_calls_made', 0)}</b></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        if report_path:
            with open(report_path, "rb") as f:
                st.download_button(
                    label="📥 Download Generated Excel Report (.xlsx)",
                    data=f,
                    file_name=f"leadpilot_{city.lower()}_{category.split()[0].lower()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        st.info("💡 You can now view and manage these records in the **Lead Database** or review drafts in **Email Outreach**.")

