import re
from typing import Tuple, Optional

# Basic RFC-5322 compatible regex for syntax validation
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

# Common dummy / sample domains that should not be contacted
DISALLOWED_DOMAINS = {
    "example.com", "example.org", "test.com", "sample.com", "domain.com",
    "placeholder.com", "none.com", "email.com", "noemail.com"
}


def validate_email_address(email: Optional[str]) -> Tuple[bool, Optional[str], str]:
    """
    Validates an email address syntax and basic domain health.
    Returns:
        (is_valid, normalized_email, reason)
    """
    if not email:
        return False, None, "Email address is empty"

    clean_email = email.strip().lower()

    if not EMAIL_REGEX.match(clean_email):
        return False, None, "Invalid email syntax"

    parts = clean_email.split("@")
    if len(parts) != 2:
        return False, None, "Malformed email address"

    user, domain = parts
    if domain in DISALLOWED_DOMAINS:
        return False, None, f"Disallowed placeholder domain: {domain}"

    # Verify domain has a dot and valid TLD length
    if "." not in domain or len(domain.split(".")[-1]) < 2:
        return False, None, "Invalid domain extension"

    return True, clean_email, "Valid"

