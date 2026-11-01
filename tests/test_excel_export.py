import os
import openpyxl
import pytest
from services.export_service import ExportService
from utils.text_sanitization import sanitize_for_excel


def test_formula_injection_sanitization():
    assert sanitize_for_excel("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert sanitize_for_excel("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_for_excel("-10+20") == "'-10+20"
    assert sanitize_for_excel("@evil") == "'@evil"
    assert sanitize_for_excel("Safe Business Name") == "Safe Business Name"


def test_excel_export_sheets_and_formatting(tmp_path):
    exporter = ExportService(output_dir=tmp_path)
    leads = [
        {
            "id": 1,
            "business_name": "Arogya Dental Clinic",
            "category": "Dental Clinic",
            "full_address": "123 Indiranagar, Bengaluru",
            "area": "Indiranagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India",
            "phone_number": "+91 98450 12345",
            "email": "contact@arogyaclinic.org",
            "maps_url": "https://maps.google.com/?q=ChIJ123",
            "website_url": None,
            "website_status": "NO_WEBSITE_FOUND",
            "verification_confidence": 0.85,
            "lead_score": 95.0,
            "priority": "High",
            "scoring_explanation": "+40 pts: No website; +15 pts: Phone",
            "contact_status": "Not contacted",
            "next_action": "Email outreach",
            "source": "Places API",
            "last_verified_at": "2026-11-01"
        },
        {
            "id": 2,
            "business_name": "=MALICIOUS_FORMULA()",
            "category": "Gym",
            "full_address": "Koramangala, Bengaluru",
            "area": "Koramangala",
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India",
            "phone_number": "+91 98200 54321",
            "email": None,
            "maps_url": "https://maps.google.com/?q=ChIJ456",
            "website_url": "https://gymsite.com",
            "website_status": "WEBSITE_FOUND",
            "verification_confidence": 0.95,
            "lead_score": 30.0,
            "priority": "Low",
            "scoring_explanation": "Existing website",
            "contact_status": "Not contacted",
            "next_action": "None",
            "source": "Places API",
            "last_verified_at": "2026-11-01"
        }
    ]

    summary = {
        "job_id": "test_job_001",
        "location": "Bengaluru, India",
        "category": "Dental & Fitness",
        "queries": "Dental in Bengaluru",
        "actual_api_usage": 5
    }

    filepath = exporter.export_to_excel(leads, search_summary=summary, min_high_priority_score=80.0)
    assert os.path.exists(filepath)

    # Open workbook and verify sheet structure
    wb = openpyxl.load_workbook(filepath)
    sheet_names = wb.sheetnames
    assert "High-Priority Leads" in sheet_names
    assert "All Prospects" in sheet_names
    assert "Needs Verification" in sheet_names
    assert "Contact History" in sheet_names
    assert "Search Summary" in sheet_names

    # Check High-Priority sheet has only lead 1 (score 95 >= 80)
    ws_high = wb["High-Priority Leads"]
    assert ws_high.max_row == 2  # 1 header + 1 record

    # Check All Prospects sheet has 2 records
    ws_all = wb["All Prospects"]
    assert ws_all.max_row == 3  # 1 header + 2 records

    # Check formula injection was sanitized in cell
    name_cell_val = ws_all.cell(row=3, column=2).value
    assert name_cell_val == "'=MALICIOUS_FORMULA()"

