import pytest
from unittest.mock import patch
from database.connection import init_db
from graph.workflow import run_lead_workflow
from services.google_places_service import google_places_service


def test_full_lead_workflow_execution():
    init_db()

    search_params = {
        "country": "India",
        "state": "Karnataka",
        "city": "Bengaluru",
        "area": "Indiranagar",
        "category": "Dental Clinic",
        "keywords": "",
        "max_results": 5,
        "min_score": 50.0,
        "budget_limit": 20
    }

    # Ensure mock discovery is used during unit test so tests never fail on external quota/restrictions
    mock_results, _, _ = google_places_service._generate_mock_places("dental clinic", 5, "India")
    with patch("services.google_places_service.google_places_service.search_places", return_value=(mock_results, 1, None)):
        final_state = run_lead_workflow(search_params)

        assert final_state["job_id"] != ""
        assert len(final_state["discovered_records"]) > 0
        assert len(final_state["persisted_leads"]) > 0
        assert final_state["excel_report_path"] is not None
        assert final_state["status"] == "COMPLETED"

        # Check lead scores and properties
        for lead in final_state["persisted_leads"]:
            assert "lead_score" in lead
            assert "priority" in lead
            assert "website_status" in lead

