import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional


def is_safe_public_url(url: Optional[str]) -> Tuple[bool, str]:
    """
    Validates a URL and enforces SSRF protection:
    - Must have http or https scheme
    - Must have a valid hostname
    - Hostname must not resolve to localhost, private IP, link-local, loopback, or reserved address
    Returns (is_safe, reason_or_normalized_url)
    """
    if not url:
        return False, "URL is empty"

    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url

    try:
        parsed = urlparse(clean_url)
        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return False, f"Unsupported scheme: {scheme}"

        hostname = parsed.hostname
        if not hostname:
            return False, "Missing hostname"

        # Check for localhost names
        lowered_host = hostname.lower()
        if lowered_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or lowered_host.endswith(".local") or lowered_host.endswith(".internal"):
            return False, f"Blocked private/local hostname: {hostname}"

        # Resolve IP and check for private / loopback / link-local addresses
        try:
            # First check if hostname is direct IP literal
            try:
                ip_obj = ipaddress.ip_address(hostname)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
                    return False, f"Blocked private IP literal: {hostname}"
            except ValueError:
                # Hostname is a domain name, resolve it
                addr_info = socket.getaddrinfo(hostname, None)
                for entry in addr_info:
                    ip_str = entry[4][0]
                    ip_obj = ipaddress.ip_address(ip_str)
                    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
                        return False, f"Hostname resolves to private IP: {ip_str}"
        except socket.gaierror:
            # DNS resolution failed - the website domain does not resolve
            return False, f"DNS resolution failed for {hostname}"
        except Exception as e:
            return False, f"Address verification error: {str(e)}"

        return True, clean_url

    except Exception as e:
        return False, f"Malformed URL: {str(e)}"


def is_social_or_directory_url(url: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Checks if a URL belongs to a social media platform or third-party directory,
    rather than being an independent business website.
    Returns (is_match, type_detected)
    """
    if not url:
        return False, None

    url_lower = url.lower()
    
    # Social media platforms
    social_domains = [
        "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
        "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com"
    ]
    for domain in social_domains:
        if domain in url_lower:
            return True, "SOCIAL_MEDIA"

    # Business directories / aggregators
    directory_domains = [
        "justdial.com", "indiamart.com", "sulekha.com", "tradeindia.com",
        "yellowpages.com", "yelp.com", "tripadvisor.com", "zomato.com",
        "swiggy.com", "magicpin.in", "google.com/maps", "goo.gl/maps"
    ]
    for domain in directory_domains:
        if domain in url_lower:
            return True, "DIRECTORY"

    return False, None

