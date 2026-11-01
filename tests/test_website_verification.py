import pytest
from unittest.mock import patch, MagicMock
from services.website_check_service import WebsiteCheckService
from utils.url_validation import is_safe_public_url, is_social_or_directory_url


def test_ssrf_protection_localhost():
    is_safe, reason = is_safe_public_url("http://localhost:8000")
    assert is_safe is False
    assert "Blocked private/local hostname" in reason


def test_ssrf_protection_private_ip():
    is_safe, reason = is_safe_public_url("http://192.168.1.1/admin")
    assert is_safe is False
    assert "Blocked private IP literal" in reason


def test_ssrf_protection_loopback():
    is_safe, reason = is_safe_public_url("http://127.0.0.1:3000")
    assert is_safe is False


def test_social_media_detection():
    is_social, kind = is_social_or_directory_url("https://www.instagram.com/my_salon_page")
    assert is_social is True
    assert kind == "SOCIAL_MEDIA"


def test_directory_detection():
    is_dir, kind = is_social_or_directory_url("https://www.justdial.com/Bengaluru/My-Clinic")
    assert is_dir is True
    assert kind == "DIRECTORY"


def test_website_verification_no_url():
    service = WebsiteCheckService()
    result = service.verify_website(None)
    assert result["status"] == "NO_WEBSITE_FOUND"
    assert result["candidate_url"] is None


def test_website_verification_social_only():
    service = WebsiteCheckService()
    result = service.verify_website("https://facebook.com/bengalurucafe")
    assert result["status"] == "SOCIAL_MEDIA_ONLY"
    assert result["confidence"] >= 0.90


@patch("requests.Session.head")
def test_website_verification_accessible(mock_head):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://www.realclinic.com"
    mock_head.return_value = mock_resp

    service = WebsiteCheckService()
    # Mock is_safe_public_url to return True for test domain
    with patch("services.website_check_service.is_safe_public_url", return_value=(True, "https://www.realclinic.com")):
        result = service.verify_website("https://www.realclinic.com")
        assert result["status"] == "WEBSITE_FOUND"
        assert result["confidence"] >= 0.95


@patch("requests.Session.head")
def test_website_verification_404_inaccessible(mock_head):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.url = "https://www.broken-site.com"
    mock_head.return_value = mock_resp

    service = WebsiteCheckService()
    with patch("services.website_check_service.is_safe_public_url", return_value=(True, "https://www.broken-site.com")):
        result = service.verify_website("https://www.broken-site.com")
        assert result["status"] == "WEBSITE_FOUND_INACCESSIBLE"

