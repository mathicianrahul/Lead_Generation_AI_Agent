import re
from typing import Optional, Tuple

try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat, geocoder
    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False


def normalize_phone_number(raw_phone: Optional[str], default_region: str = "IN") -> Tuple[Optional[str], Optional[str], bool]:
    """
    Normalizes a phone number.
    Returns:
        (e164_format, national_format, is_valid)
    """
    if not raw_phone:
        return None, None, False

    clean_raw = str(raw_phone).strip()
    if not clean_raw:
        return None, None, False

    if HAS_PHONENUMBERS:
        try:
            parsed = phonenumbers.parse(clean_raw, default_region)
            is_valid = phonenumbers.is_valid_number(parsed)
            if is_valid or phonenumbers.is_possible_number(parsed):
                e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
                national = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)
                return e164, national, is_valid
        except Exception:
            pass

    # Fallback heuristic normalization (e.g. for Indian numbers)
    digits = re.sub(r'\D', '', clean_raw)
    if not digits:
        return None, None, False

    # Check for Indian standard 10-digit mobile/landline with optional 0 or 91 prefix
    if len(digits) == 10:
        e164 = f"+91{digits}"
        national = f"{digits[:5]} {digits[5:]}"
        return e164, national, True
    elif len(digits) == 11 and digits.startswith("0"):
        e164 = f"+91{digits[1:]}"
        national = f"{digits[1:6]} {digits[6:]}"
        return e164, national, True
    elif len(digits) == 12 and digits.startswith("91"):
        e164 = f"+{digits}"
        national = f"{digits[2:7]} {digits[7:]}"
        return e164, national, True
    elif len(digits) >= 7:
        prefix = "+" if clean_raw.startswith("+") else "+91" if default_region == "IN" else "+"
        return f"{prefix}{digits}", digits, False

    return None, None, False

