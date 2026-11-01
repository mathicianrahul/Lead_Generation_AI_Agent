import os
import streamlit as st
import pandas as pd
from pathlib import Path

from database.connection import SessionLocal
from database.repository import LeadRepository
from services.export_service import export_service
from config.settings import settings


def render_reports():
    st.markdown('<div class="section-title">Reports & Data Exports</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subtitle">Generate formatted multi-sheet Excel reports (.xlsx) and clean CSV spreadsheets with security protections.</div>', unsafe_allow_html=True)

    db = SessionLocal()
    try:
        repo = LeadRepository(db)
        leads_all, count = repo.filter_leads(limit=1000)

        # Convert leads to dict representation for export
        lead_dicts = []
        for l in leads_all:
            lead_dicts.append({
                "id": l.id,
                "business_name": l.business_name,
                "category": l.category,
                "full_address": l.full_address,
                "area": l.area,
                "city": l.city,
                "state": l.state,
                "country": l.country,
                "phone_number": l.phone_number,
                "email": l.emails[0].email_address if l.emails else None,
                "maps_url": l.maps_url,
                "website_url": l.website_url,
                "website_status": l.website_status,
                "verification_confidence": l.verification_confidence,
                "lead_score": l.lead_score,
                "priority": l.priority,
                "scoring_explanation": l.scoring_explanation,
                "contact_status": l.contact_status,
                "next_action": "Follow-up",
                "source": "Places API" if not l.is_demo else "Simulated Data (Demo Mode)",
                "last_verified_at": str(l.last_verified_at)[:10] if l.last_verified_at else None,
                "is_demo": l.is_demo
            })

        st.markdown(f"**Database contains {count} leads ready for export.**")

        c_exp1, c_exp2 = st.columns(2)

        with c_exp1:
            st.markdown("### Generate Fresh Multi-Sheet Excel")
            min_score = st.slider("High-Priority Score Threshold for Sheet 1", min_value=50, max_value=90, value=80, step=5)
            file_prefix = st.text_input("Report Filename Prefix", value="leadpilot_report")

            if st.button("📊 Generate Complete Excel Report (.xlsx)", type="primary", use_container_width=True):
                if not lead_dicts:
                    st.warning("Database is empty. Please run a lead search first.")
                else:
                    with st.spinner("Generating formatted Excel workbook with 5 sheets..."):
                        summary_info = {
                            "job_id": "manual_export",
                            "location": "All Locations",
                            "category": "All Categories",
                            "queries": "Export All Filtered Records",
                            "actual_api_usage": 0
                        }
                        path = export_service.export_to_excel(
                            leads=lead_dicts,
                            search_summary=summary_info,
                            filename_prefix=file_prefix,
                            min_high_priority_score=float(min_score)
                        )
                        st.success(f"Report generated: `{os.path.basename(path)}`")
                        with open(path, "rb") as f:
                            st.download_button(
                                label="📥 Click to Download Excel File (.xlsx)",
                                data=f,
                                file_name=os.path.basename(path),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )

        with c_exp2:
            st.markdown("### Generate CSV Spreadsheet")
            st.caption("Clean, formula-injection protected CSV file compatible with CRMs and Google Sheets.")
            csv_prefix = st.text_input("CSV Filename Prefix", value="leadpilot_data")

            if st.button("📄 Generate Clean CSV Export (.csv)", use_container_width=True):
                if not lead_dicts:
                    st.warning("Database is empty. Please run a lead search first.")
                else:
                    with st.spinner("Sanitizing and formatting CSV..."):
                        csv_path = export_service.export_to_csv(lead_dicts, filename_prefix=csv_prefix)
                        st.success(f"CSV generated: `{os.path.basename(csv_path)}`")
                        with open(csv_path, "rb") as f:
                            st.download_button(
                                label="📥 Click to Download CSV File (.csv)",
                                data=f,
                                file_name=os.path.basename(csv_path),
                                mime="text/csv",
                                use_container_width=True
                            )

        st.write("---")

        # Previously Generated Reports Browser
        st.subheader("Generated Export Archives")
        exports_dir = settings.exports_dir
        export_files = [f for f in exports_dir.glob("*.*") if f.suffix in (".xlsx", ".csv")]

        if export_files:
            file_data = []
            for f in sorted(export_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                size_kb = f.stat().st_size / 1024
                file_data.append({
                    "Filename": f.name,
                    "Type": f.suffix.upper()[1:],
                    "Size (KB)": f"{size_kb:.1f}",
                    "Created At": str(pd.to_datetime(f.stat().st_mtime, unit='s'))[:19]
                })
            st.dataframe(pd.DataFrame(file_data), use_container_width=True, hide_index=True)
        else:
            st.info("No export files created yet.")

    finally:
        db.close()

