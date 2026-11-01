import requests
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from utils.url_validation import is_safe_public_url, is_social_or_directory_url
from config.settings import settings
from config.logging_config import logger


class WebsiteCheckService:
    def __init__(self, timeout: int = settings.http_timeout_seconds, max_redirects: int = settings.max_redirects):
        self.timeout = timeout
        self.max_redirects = max_redirects
        # Custom user-agent identifying the verification probe politely
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) LeadPilotAI-Verification/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def verify_website(self, raw_url: Optional[str], business_name: str = "") -> Dict[str, Any]:
        """
        Executes a safe, evidence-based verification of a website URL.
        Returns a structured dictionary with:
            - status: WEBSITE_FOUND, WEBSITE_FOUND_ACCESSIBLE, WEBSITE_FOUND_INACCESSIBLE,
                      SOCIAL_MEDIA_ONLY, DIRECTORY_ONLY, NO_WEBSITE_FOUND, UNVERIFIED, CHECK_FAILED
            - confidence: float between 0.0 and 1.0
            - evidence: human-readable explanation
            - candidate_url: normalized URL or None
            - error: optional error string
        """
        if not raw_url or not str(raw_url).strip():
            return {
                "status": "NO_WEBSITE_FOUND",
                "confidence": 0.85,
                "evidence": "No website URL provided in Google Maps listing after initial search.",
                "candidate_url": None,
                "error": None
            }

        url_str = str(raw_url).strip()

        # Check if URL belongs to social media or third-party directory
        is_platform, platform_type = is_social_or_directory_url(url_str)
        if is_platform:
            if platform_type == "SOCIAL_MEDIA":
                return {
                    "status": "SOCIAL_MEDIA_ONLY",
                    "confidence": 0.95,
                    "evidence": f"URL points to a social media profile ({url_str}), not an independent business website.",
                    "candidate_url": url_str,
                    "error": None
                }
            elif platform_type == "DIRECTORY":
                return {
                    "status": "DIRECTORY_ONLY",
                    "confidence": 0.90,
                    "evidence": f"URL points to a third-party marketplace/directory listing ({url_str}).",
                    "candidate_url": url_str,
                    "error": None
                }

        # SSRF and Hostname Safety Check
        is_safe, check_result = is_safe_public_url(url_str)
        if not is_safe:
            # If DNS failed or blocked private IP
            if "DNS resolution failed" in check_result:
                return {
                    "status": "CHECK_FAILED",
                    "confidence": 0.70,
                    "evidence": f"Domain could not be resolved via DNS: {check_result}. Website may be expired or offline.",
                    "candidate_url": url_str,
                    "error": check_result
                }
            return {
                "status": "CHECK_FAILED",
                "confidence": 0.50,
                "evidence": f"Safety check rejected URL for security reasons: {check_result}",
                "candidate_url": url_str,
                "error": check_result
            }

        target_url = check_result

        # Perform safe HTTP request with limited redirects and timeout
        try:
            session = requests.Session()
            session.max_redirects = self.max_redirects

            # Use HEAD request first for efficiency; fall back to GET if 405 Method Not Allowed
            response = None
            try:
                response = session.head(
                    target_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=True
                )
            except requests.exceptions.RequestException:
                # Retry with GET in case server blocks HEAD
                response = session.get(
                    target_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=True,
                    stream=True  # Avoid downloading large bodies
                )

            status_code = response.status_code if response else 0

            # Re-check final URL after redirects for social media / SSRF
            final_url = response.url if response else target_url
            is_redirect_platform, redirect_platform_type = is_social_or_directory_url(final_url)
            if is_redirect_platform:
                return {
                    "status": "SOCIAL_MEDIA_ONLY" if redirect_platform_type == "SOCIAL_MEDIA" else "DIRECTORY_ONLY",
                    "confidence": 0.95,
                    "evidence": f"Website redirected to {final_url} ({redirect_platform_type}).",
                    "candidate_url": final_url,
                    "error": None
                }

            if 200 <= status_code < 400:
                return {
                    "status": "WEBSITE_FOUND",
                    "confidence": 0.98,
                    "evidence": f"Independent business website confirmed accessible (HTTP {status_code}). Final URL: {final_url}",
                    "candidate_url": final_url,
                    "error": None
                }
            elif status_code in (401, 403):
                return {
                    "status": "WEBSITE_FOUND",
                    "confidence": 0.85,
                    "evidence": f"Independent website exists but returned access challenge (HTTP {status_code}). Likely has bot protection/Cloudflare.",
                    "candidate_url": target_url,
                    "error": f"HTTP {status_code}"
                }
            elif status_code == 404:
                return {
                    "status": "WEBSITE_FOUND_INACCESSIBLE",
                    "confidence": 0.75,
                    "evidence": f"Website URL is listed but returned 404 Not Found at {target_url}.",
                    "candidate_url": target_url,
                    "error": "HTTP 404"
                }
            else:
                return {
                    "status": "WEBSITE_FOUND_INACCESSIBLE",
                    "confidence": 0.65,
                    "evidence": f"Website URL listed but returned server response HTTP {status_code}.",
                    "candidate_url": target_url,
                    "error": f"HTTP {status_code}"
                }

        except requests.exceptions.SSLError as ssl_err:
            return {
                "status": "CHECK_FAILED",
                "confidence": 0.60,
                "evidence": f"SSL/TLS Certificate error when reaching {target_url}: {str(ssl_err)[:80]}",
                "candidate_url": target_url,
                "error": "SSL_ERROR"
            }
        except requests.exceptions.Timeout:
            return {
                "status": "CHECK_FAILED",
                "confidence": 0.50,
                "evidence": f"Connection timed out after {self.timeout}s when verifying {target_url}.",
                "candidate_url": target_url,
                "error": "TIMEOUT"
            }
        except requests.exceptions.ConnectionError as conn_err:
            return {
                "status": "CHECK_FAILED",
                "confidence": 0.65,
                "evidence": f"Connection refused or unreachable for {target_url}.",
                "candidate_url": target_url,
                "error": "CONNECTION_ERROR"
            }
        except Exception as e:
            return {
                "status": "CHECK_FAILED",
                "confidence": 0.40,
                "evidence": f"Unexpected verification error: {str(e)[:100]}",
                "candidate_url": target_url,
                "error": str(e)
            }


website_check_service = WebsiteCheckService()

