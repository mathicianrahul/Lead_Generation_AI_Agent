import pytest
from utils.deduplication import is_duplicate_record, merge_business_records, normalize_business_name
from utils.phone_utils import normalize_phone_number


def test_place_id_deduplication():
    existing = [
        {"place_id": "ChIJ123456", "business_name": "Smile Dental Clinic", "city": "Bengaluru"}
    ]
    candidate = {
        "place_id": "ChIJ123456", "business_name": "Smile Dental", "city": "Bengaluru"
    }
    is_dup, matched, reason = is_duplicate_record(candidate, existing)
    assert is_dup is True
    assert reason == "PLACE_ID_MATCH"


def test_phone_number_deduplication_different_formats():
    # Both normalize to +919845012345
    phone1_e164, _, _ = normalize_phone_number("098450 12345", "IN")
    phone2_e164, _, _ = normalize_phone_number("+91-98450-12345", "IN")
    assert phone1_e164 == phone2_e164

    existing = [
        {"place_id": "p1", "phone_number": phone1_e164, "business_name": "Kiran Cafe"}
    ]
    candidate = {
        "place_id": "p2", "phone_number": phone2_e164, "business_name": "Kiran Food Hub"
    }
    is_dup, matched, reason = is_duplicate_record(candidate, existing)
    assert is_dup is True
    assert reason == "PHONE_MATCH"


def test_name_and_address_deduplication():
    existing = [
        {
            "place_id": "p1",
            "business_name": "Apex Fitness Pvt Ltd",
            "full_address": "123 100ft Road, Indiranagar, Bengaluru"
        }
    ]
    candidate = {
        "place_id": "p2",
        "business_name": "Apex Fitness",
        "full_address": "123 100ft Road, Indiranagar, Bengaluru"
    }
    is_dup, matched, reason = is_duplicate_record(candidate, existing)
    assert is_dup is True
    assert reason == "NAME_AND_ADDRESS_MATCH"


def test_different_locations_not_duplicate():
    existing = [
        {"place_id": "p1", "business_name": "Royal Cafe", "full_address": "Koramangala, Bengaluru"}
    ]
    candidate = {
        "place_id": "p2", "business_name": "Royal Cafe", "full_address": "Connaught Place, Delhi"
    }
    is_dup, matched, reason = is_duplicate_record(candidate, existing)
    assert is_dup is False


def test_safe_field_merge():
    canonical = {
        "place_id": "p1",
        "business_name": "Arogya Clinic",
        "phone_number": None,
        "website_url": None
    }
    incoming = {
        "place_id": "p1",
        "business_name": "Arogya Clinic",
        "phone_number": "+91 98450 12345",
        "website_url": "https://arogyaclinic.org"
    }
    merged, conflicts = merge_business_records(canonical, incoming)
    assert merged["phone_number"] == "+91 98450 12345"
    assert merged["website_url"] == "https://arogyaclinic.org"
    assert len(conflicts) == 0

