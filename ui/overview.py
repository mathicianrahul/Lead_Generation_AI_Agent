import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database.connection import SessionLocal
from database.repository import LeadRepository


def render_overview():
    st.markdown('<div class="section-title">Executive Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Real-time performance metrics, lead distribution, and outreach status.</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        metrics = repo.get_metrics()
        cat_counts = repo.get_category_counts()
        city_counts = repo.get_city_counts()
        web_counts = repo.get_website_status_counts()
        priority_counts = repo.get_priority_counts()
        contact_counts = repo.get_contact_status_counts()
        recent_jobs = repo.get_recent_jobs(limit=5)
    finally:
        db.close()

    # Row 1: Key Performance Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Discovered</div>
            <div class="metric-value">{metrics['total_discovered']}</div>
            <div class="metric-sub">Unique business listings</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label" style="color: #B91C1C;">No Website Found</div>
            <div class="metric-value" style="color: #DC2626;">{metrics['no_website_found']}</div>
            <div class="metric-sub">Prime website prospects</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label" style="color: #15803D;">High-Priority Leads</div>
            <div class="metric-value" style="color: #16A34A;">{metrics['high_priority']}</div>
            <div class="metric-sub">Score 80–100 / Verified Phone</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label" style="color: #2563EB;">Pipeline Value</div>
            <div class="metric-value" style="color: #1D4ED8;">₹{metrics['pipeline_value']:,.0f}</div>
            <div class="metric-sub">{metrics['interested']} active / {metrics['converted']} converted</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Row 2: Secondary Indicators
    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("Social Media Only", metrics['social_only'], help="Businesses with Instagram/FB profile but no domain")
    with c6:
        st.metric("Unverified Status", metrics['unverified'], help="Leads requiring manual or secondary verification")
    with c7:
        st.metric("Pending Email Approval", metrics['pending_approval'], help="Drafted emails awaiting human approval")
    with c8:
        st.metric("Emails Sent", metrics['emails_sent'], help="Outreach delivered via authorized Gmail")

    st.write("---")

    # Row 3: Interactive Visualizations
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Website Status Distribution")
        if web_counts:
            df_web = pd.DataFrame(web_counts, columns=["Status", "Count"])
            fig_web = px.pie(
                df_web,
                names="Status",
                values="Count",
                hole=0.45,
                color="Status",
                color_discrete_map={
                    "NO_WEBSITE_FOUND": "#EF4444",
                    "SOCIAL_MEDIA_ONLY": "#8B5CF6",
                    "WEBSITE_FOUND": "#3B82F6",
                    "WEBSITE_FOUND_ACCESSIBLE": "#2563EB",
                    "UNVERIFIED": "#F59E0B",
                    "CHECK_FAILED": "#6B7280"
                }
            )
            fig_web.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig_web, use_container_width=True)
        else:
            st.info("No business records discovered yet. Run a search to view distribution.")

    with col_chart2:
        st.subheader("Lead Priority Distribution")
        if priority_counts:
            df_pri = pd.DataFrame(priority_counts, columns=["Priority", "Count"])
            fig_pri = px.bar(
                df_pri,
                x="Priority",
                y="Count",
                color="Priority",
                color_discrete_map={
                    "High": "#10B981",
                    "Medium": "#FBBF24",
                    "Low": "#94A3B8"
                }
            )
            fig_pri.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False)
            st.plotly_chart(fig_pri, use_container_width=True)
        else:
            st.info("No lead scoring data yet.")

    # Row 4: Category & Geography Breakdown
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.subheader("Top Business Categories")
        if cat_counts:
            df_cat = pd.DataFrame(cat_counts, columns=["Category", "Leads"])
            fig_cat = px.bar(df_cat, x="Leads", y="Category", orientation='h', color="Leads", color_continuous_scale="Blues")
            fig_cat.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("Category analytics will appear here after your first search.")

    with col_chart4:
        st.subheader("Outreach & Conversion Funnel")
        if contact_counts:
            df_funnel = pd.DataFrame(contact_counts, columns=["Stage", "Count"])
            fig_funnel = px.bar(df_funnel, x="Stage", y="Count", color="Count", color_continuous_scale="Purples")
            fig_funnel.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.info("CRM pipeline statistics will populate as you engage leads.")

    st.write("---")

    # Row 5: Recent Search Job History
    st.subheader("Recent Search Execution History")
    if recent_jobs:
        job_rows = []
        for j in recent_jobs:
            job_rows.append({
                "Job ID": j.id,
                "Status": j.status,
                "Started At": str(j.started_at)[:19] if j.started_at else "",
                "Discovered": j.discovered_count,
                "Unique Leads": j.unique_count,
                "API Operations": j.actual_api_usage or j.estimated_api_usage,
                "Summary": j.error_summary or "Completed"
            })
        st.dataframe(pd.DataFrame(job_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No search executions recorded in this environment. Head over to 'Find Leads' to begin.")

