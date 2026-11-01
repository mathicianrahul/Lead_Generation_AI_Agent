import pytest
from services.scoring_service import ScoringService
from config.settings import ScoringWeights


def test_scoring_business_without_website():
    scorer = ScoringService()
    lead = {
        "website_status": "NO_WEBSITE_FOUND",
        "phone_number": "+91 98450 12345",
        "email": "contact@clinic.example.com",
        "review_count": 25,
        "rating": 4.6,
        "category": "Dental Clinic"
    }
    score, priority, explanation = scorer.calculate_lead_score(lead)
    # Expected: 40 (no website) + 15 (phone) + 15 (email) + 15 (reviews) + 15 (dental high value) = 100
    assert score == 100.0
    assert priority == "High"
    assert "No independent business website found" in explanation


def test_scoring_business_with_existing_website():
    scorer = ScoringService()
    lead = {
        "website_status": "WEBSITE_FOUND",
        "phone_number": "+91 98450 12345",
        "email": "info@sample.com",
        "review_count": 5,
        "rating": 4.0,
        "category": "Retail Shop"
    }
    score, priority, explanation = scorer.calculate_lead_score(lead)
    # Website opportunity is 0
    assert score < 60.0
    assert priority == "Low"
    assert "Confirmed independent website already exists" in explanation


def test_scoring_social_media_only():
    scorer = ScoringService()
    lead = {
        "website_status": "SOCIAL_MEDIA_ONLY",
        "phone_number": "+91 98450 12345",
        "review_count": 30,
        "rating": 4.8,
        "category": "Beauty Salon"
    }
    score, priority, explanation = scorer.calculate_lead_score(lead)
    # 35 (social) + 15 (phone) + 0 (no email) + 15 (reviews) + 15 (high val cat) = 80
    assert score >= 80.0
    assert priority == "High"


def test_scoring_missing_contact_info():
    scorer = ScoringService()
    lead = {
        "website_status": "NO_WEBSITE_FOUND",
        "phone_number": None,
        "email": None,
        "review_count": 0,
        "rating": 0.0,
        "category": "Local Store"
    }
    score, priority, explanation = scorer.calculate_lead_score(lead)
    # 40 (no web) + 0 + 0 + 0 + 5 = 45
    assert score == 45.0
    assert priority == "Low"

