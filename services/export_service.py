import os
import re
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config.settings import settings
from config.logging_config import logger
from utils.text_sanitization import sanitize_for_excel


class ExportService:
    def __init__(self, output_dir: Path = settings.exports_dir):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, prefix: str, ext: str = "xlsx") -> str:
        safe_prefix = re.sub(r'[^\w\-]', '_', prefix.lower())
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_prefix}_{timestamp}.{ext}"

    def export_to_excel(
        self,
        leads: List[Dict[str, Any]],
        search_summary: Optional[Dict[str, Any]] = None,
        contact_history: Optional[List[Dict[str, Any]]] = None,
        filename_prefix: str = "leadpilot_leads",
        min_high_priority_score: float = 80.0
    ) -> str:
        """
        Generates a professional, multi-sheet formatted Excel workbook with:
        1. High-Priority Leads
        2. All Prospects
        3. Needs Verification
        4. Contact History
        5. Search Summary
        Returns the absolute filepath of the generated workbook.
        """
        filename = self._generate_filename(filename_prefix, "xlsx")
        filepath = self.output_dir / filename

        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # Style definitions
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        regular_font = Font(name="Segoe UI", size=10)
        link_font = Font(name="Segoe UI", size=10, color="2563EB", underline="single")
        
        thin_border = Border(
            left=Side(style='thin', color='E2E8F0'),
            right=Side(style='thin', color='E2E8F0'),
            top=Side(style='thin', color='E2E8F0'),
            bottom=Side(style='thin', color='E2E8F0')
        )
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        # Column definitions
        columns = [
            ("Lead ID", "id"),
            ("Business Name", "business_name"),
            ("Business Category", "category"),
            ("Full Address", "full_address"),
            ("Area", "area"),
            ("City", "city"),
            ("State", "state"),
            ("Country", "country"),
            ("Phone Number", "phone_number"),
            ("Public Business Email", "email"),
            ("Google Maps Link", "maps_url"),
            ("Website URL", "website_url"),
            ("Website Status", "website_status"),
            ("Verification Confidence", "verification_confidence"),
            ("Lead Score", "lead_score"),
            ("Priority", "priority"),
            ("Score Explanation", "scoring_explanation"),
            ("Contact Status", "contact_status"),
            ("Next Action", "next_action"),
            ("Data Source", "source"),
            ("Last Verified", "last_verified_at")
        ]

        def format_sheet(ws, title: str, row_records: List[Dict[str, Any]]):
            ws.title = title
            ws.views.sheetView[0].showGridLines = True

            # Write header
            headers = [c[0] for c in columns]
            ws.append(headers)

            for col_num in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=False)
                cell.border = thin_border
            ws.row_dimensions[1].height = 28

            # Write data rows
            for row_idx, r in enumerate(row_records, start=2):
                row_vals = []
                for col_name, key in columns:
                    val = r.get(key)
                    # Protect against formula injection
                    sanitized = sanitize_for_excel(val)
                    row_vals.append(sanitized)
                ws.append(row_vals)

                # Format row cells
                is_even = (row_idx % 2 == 0)
                for col_num in range(1, len(headers) + 1):
                    cell = ws.cell(row=row_idx, column=col_num)
                    cell.font = regular_font
                    cell.border = thin_border
                    if is_even:
                        cell.fill = zebra_fill
                    cell.alignment = Alignment(vertical="center")

                    # Add hyperlinks for URLs
                    col_key = columns[col_num - 1][1]
                    val_str = str(r.get(col_key) or "")
                    if col_key in ("maps_url", "website_url") and val_str.startswith("http"):
                        cell.hyperlink = val_str
                        cell.font = link_font

            # Freeze headers and enable autofilter
            ws.freeze_panes = "A2"
            if row_records:
                last_col_letter = get_column_letter(len(headers))
                ws.auto_filter.ref = f"A1:{last_col_letter}{len(row_records) + 1}"

            # Auto-fit column widths
            for col_num in range(1, len(headers) + 1):
                max_len = len(str(headers[col_num - 1]))
                for row_idx in range(2, min(len(row_records) + 2, 50)):
                    val = ws.cell(row=row_idx, column=col_num).value
                    if val is not None:
                        max_len = max(max_len, min(len(str(val)), 40))
                col_letter = get_column_letter(col_num)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # 1. High Priority Leads (Score >= threshold)
        high_leads = [l for l in leads if (l.get("lead_score") or 0.0) >= min_high_priority_score]
        ws_high = wb.create_sheet()
        format_sheet(ws_high, "High-Priority Leads", high_leads)

        # 2. All Prospects
        ws_all = wb.create_sheet()
        format_sheet(ws_all, "All Prospects", leads)

        # 3. Needs Verification (UNVERIFIED or CHECK_FAILED)
        needs_verif = [l for l in leads if l.get("website_status") in ("UNVERIFIED", "CHECK_FAILED")]
        ws_verif = wb.create_sheet()
        format_sheet(ws_verif, "Needs Verification", needs_verif)

        # 4. Contact History
        ws_hist = wb.create_sheet(title="Contact History")
        ws_hist.views.sheetView[0].showGridLines = True
        hist_headers = ["Lead ID", "Contact Method", "Event Type", "Event Date", "Notes", "Next Action", "Next Action Date"]
        ws_hist.append(hist_headers)
        for col_num in range(1, len(hist_headers) + 1):
            cell = ws_hist.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_hist.row_dimensions[1].height = 26

        if contact_history:
            for r_idx, h in enumerate(contact_history, start=2):
                ws_hist.append([
                    h.get("lead_id"),
                    h.get("contact_method"),
                    h.get("event_type"),
                    str(h.get("event_timestamp") or ""),
                    sanitize_for_excel(h.get("notes")),
                    sanitize_for_excel(h.get("next_action")),
                    str(h.get("next_action_date") or "")
                ])
                for col_num in range(1, len(hist_headers) + 1):
                    c = ws_hist.cell(row=r_idx, column=col_num)
                    c.font = regular_font
                    c.border = thin_border
        ws_hist.freeze_panes = "A2"

        # 5. Search Summary Sheet
        ws_summary = wb.create_sheet(title="Search Summary")
        ws_summary.views.sheetView[0].showGridLines = True
        summary_title_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        summary_title_font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")

        ws_summary.merge_cells("A1:C1")
        title_cell = ws_summary["A1"]
        title_cell.value = "LeadPilot AI - Lead Generation Execution Summary"
        title_cell.fill = summary_title_fill
        title_cell.font = summary_title_font
        title_cell.alignment = Alignment(horizontal="left", vertical="center")
        ws_summary.row_dimensions[1].height = 36

        s_data = search_summary or {}
        summary_metrics = [
            ("Report Generated At", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Search Job ID", s_data.get("job_id", "N/A")),
            ("Location Target", s_data.get("location", "N/A")),
            ("Category Target", s_data.get("category", "N/A")),
            ("Search Queries Executed", s_data.get("queries", "N/A")),
            ("Total Records Discovered", len(leads)),
            ("High-Priority Leads (Score >= 80)", len(high_leads)),
            ("Businesses with No Website Found", len([l for l in leads if l.get("website_status") == "NO_WEBSITE_FOUND"])),
            ("Businesses with Social Media Only", len([l for l in leads if l.get("website_status") == "SOCIAL_MEDIA_ONLY"])),
            ("Businesses with Existing Websites", len([l for l in leads if l.get("website_status") in ("WEBSITE_FOUND", "WEBSITE_FOUND_ACCESSIBLE")])),
            ("Unverified / Needs Verification", len(needs_verif)),
            ("API Calls Used", s_data.get("actual_api_usage", 0)),
            ("Data Mode", "DEMO MODE (Simulated)" if any(l.get("is_demo") for l in leads) else "LIVE GOOGLE PLACES API")
        ]

        for s_idx, (k, v) in enumerate(summary_metrics, start=3):
            cell_k = ws_summary.cell(row=s_idx, column=1, value=k)
            cell_v = ws_summary.cell(row=s_idx, column=2, value=sanitize_for_excel(v))
            cell_k.font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
            cell_v.font = regular_font
            cell_k.border = thin_border
            cell_v.border = thin_border
            cell_k.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

        ws_summary.column_dimensions["A"].width = 38
        ws_summary.column_dimensions["B"].width = 50

        wb.save(filepath)
        logger.info("Successfully exported %d leads to %s", len(leads), filepath)
        return str(filepath)

    def export_to_csv(self, leads: List[Dict[str, Any]], filename_prefix: str = "leadpilot_leads") -> str:
        """Exports lead records to a sanitized CSV file."""
        filename = self._generate_filename(filename_prefix, "csv")
        filepath = self.output_dir / filename

        df = pd.DataFrame(leads)
        # Apply formula sanitization
        for col in df.columns:
            df[col] = df[col].apply(sanitize_for_excel)

        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info("Successfully exported CSV to %s", filepath)
        return str(filepath)


export_service = ExportService()

