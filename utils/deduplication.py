import re
import difflib
from typing import Dict, Any, Optional, Tuple, List


def normalize_business_name(name: Optional[str]) -> str:
    """Normalizes a business name by removing punctuation, extra spaces, and common suffixes."""
    if not name:
        return ""
    # Lowercase and replace punctuation with spaces
    cleaned = re.sub(r'[^\w\s]', ' ', name.lower())
    # Remove common company tokens
    tokens_to_remove = {"pvt", "ltd", "private", "limited", "llp", "inc", "co", "enterprise", "enterprises"}
    tokens = [t for t in cleaned.split() if t not in tokens_to_remove]
    return " ".join(tokens)


def normalize_address(address: Optional[str]) -> str:
    """Normalizes an address string for deduplication."""
    if not address:
        return ""
    cleaned = re.sub(r'[^\w\s]', ' ', address.lower())
    return " ".join(cleaned.split())


def calculate_name_similarity(name1: str, name2: str) -> float:
    """Calculates string similarity ratio between two business names."""
    n1 = normalize_business_name(name1)
    n2 = normalize_business_name(name2)
    if not n1 or not n2:
        return 0.0
    return difflib.SequenceMatcher(None, n1, n2).ratio()


def is_duplicate_record(candidate: Dict[str, Any], existing_records: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Checks if a candidate business record matches any existing record.
    Deduplication precedence:
    1. Google Place ID
    2. Normalized Phone Number
    3. Normalized Name + Address exact match
    4. Fuzzy Name match (>= 0.88) within same City and Area
    """
    cand_place_id = candidate.get("place_id")
    cand_phone = candidate.get("phone_number")
    cand_name = normalize_business_name(candidate.get("business_name"))
    cand_addr = normalize_address(candidate.get("full_address"))
    cand_city = (candidate.get("city") or "").strip().lower()
    cand_area = (candidate.get("area") or "").strip().lower()

    for existing in existing_records:
        # 1. Place ID check
        if cand_place_id and existing.get("place_id") == cand_place_id:
            return True, existing, "PLACE_ID_MATCH"

        # 2. Normalized phone number check
        if cand_phone and existing.get("phone_number") and cand_phone == existing.get("phone_number"):
            return True, existing, "PHONE_MATCH"

        # 3. Normalized Name + Address check
        exist_name = normalize_business_name(existing.get("business_name"))
        exist_addr = normalize_address(existing.get("full_address"))
        if cand_name and exist_name and cand_name == exist_name:
            if cand_addr and exist_addr and cand_addr == exist_addr:
                return True, existing, "NAME_AND_ADDRESS_MATCH"

        # 4. Fuzzy Name match in same City/Area
        exist_city = (existing.get("city") or "").strip().lower()
        if cand_name and exist_name and cand_city and exist_city and cand_city == exist_city:
            sim = calculate_name_similarity(cand_name, exist_name)
            if sim >= 0.88:
                # If area is present and matches or is part of address
                if not cand_area or not existing.get("area") or cand_area == (existing.get("area") or "").strip().lower():
                    return True, existing, f"FUZZY_NAME_MATCH_{int(sim*100)}%"

    return False, None, "UNIQUE"


def merge_business_records(canonical: Dict[str, Any], incoming: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Safely merges incoming fields into canonical record.
    Preserves existing canonical values, populates missing fields, and notes conflicts.
    """
    merged = dict(canonical)
    conflicts = []

    fields_to_fill = [
        "phone_number", "website_url", "rating", "review_count",
        "latitude", "longitude", "area", "full_address"
    ]

    for field in fields_to_fill:
        existing_val = merged.get(field)
        incoming_val = incoming.get(field)

        if not existing_val and incoming_val:
            merged[field] = incoming_val
        elif existing_val and incoming_val and existing_val != incoming_val:
            conflicts.append(f"{field}: kept '{existing_val}', skipped incoming '{incoming_val}'")

    return merged, conflicts

