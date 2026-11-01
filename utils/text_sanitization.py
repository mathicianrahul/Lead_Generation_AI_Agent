import re
from typing import Any, Optional


def sanitize_for_excel(val: Any) -> Any:
    """
    Prevents spreadsheet formula injection (CSV/Excel Formula Injection).
    If a string starts with =, +, -, @, tab, or carriage return, prepend a single quote '.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val
    
    s = str(val).strip()
    if not s:
        return ""
    
    # Check if the string starts with characters that could trigger formulas in Excel/Sheets
    if s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def sanitize_string(text: Optional[str]) -> str:
    """Cleans up extra whitespaces and control characters from text."""
    if not text:
        return ""
    # Remove control characters except newline and tab
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(text))
    return " ".join(cleaned.split())

