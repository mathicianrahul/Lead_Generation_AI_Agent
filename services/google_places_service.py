import time
import requests
from typing import Dict, Any, List, Optional, Tuple

from config.settings import settings
from config.logging_config import logger
from utils.phone_utils import normalize_phone_number


class GooglePlacesService:
    """
    Official Google Places API integration service.
    Handles Text Search, Place Details, pagination, quota tracking,
    and safe fallback to clearly labeled demo data when credentials are not configured.
    """
    BASE_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    BASE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    NEW_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.google_maps_api_key

    def is_configured(self) -> bool:
        key = self.api_key or settings.google_maps_api_key
        return bool(key and key.strip() and not key.startswith("your_"))

    def search_places(
        self,
        query: str,
        max_results: int = 20,
        country: str = "India"
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """
        Executes a Places search query.
        Tries the Places API (New) first, then falls back to Classic Text Search.
        Returns:
            (records_list, api_calls_made, error_message_if_any)
        """
        active_key = self.api_key or settings.google_maps_api_key
        if not self.is_configured():
            logger.info("Google Places API key not configured or demo mode active. Generating labeled mock discovery records.")
            return self._generate_mock_places(query, max_results, country)

        # 1. Attempt Places API (New)
        new_places, calls, new_err = self._search_places_new(query, max_results, country, active_key)
        if new_places or (new_err and "ZERO_RESULTS" in new_err):
            return new_places, calls, None
        
        # If new endpoint had permission error or legacy fallback needed
        legacy_places, leg_calls, leg_err = self._search_places_legacy(query, max_results, country, active_key)
        total_calls = calls + leg_calls
        if legacy_places or (leg_err and "ZERO_RESULTS" in leg_err):
            return legacy_places, total_calls, None

        # Both returned errors: compile helpful error message
        combined_error = new_err or leg_err or "Unknown Places API error"
        return [], total_calls, combined_error

    def _search_places_new(
        self,
        query: str,
        max_results: int,
        country: str,
        key: str
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """Executes search using Google Places API (New)."""
        full_query = f"{query}, {country}" if country and country.lower() not in query.lower() else query
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.primaryTypeDisplayName,places.formattedAddress,"
                "places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri,"
                "places.rating,places.userRatingCount,places.location,places.googleMapsUri"
            )
        }
        payload = {
            "textQuery": full_query,
            "pageSize": min(max_results, 20)
        }

        try:
            resp = requests.post(self.NEW_SEARCH_URL, headers=headers, json=payload, timeout=settings.http_timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                raw_places = data.get("places", [])
                if not raw_places:
                    return [], 1, "ZERO_RESULTS"

                formatted = []
                for p in raw_places:
                    display_name = p.get("displayName", {}).get("text") or "Business"
                    cat_name = p.get("primaryTypeDisplayName", {}).get("text") or "Local Business"
                    raw_phone = p.get("nationalPhoneNumber") or p.get("internationalPhoneNumber")
                    norm_phone, _, _ = normalize_phone_number(raw_phone, "IN")
                    loc = p.get("location", {})

                    formatted.append({
                        "place_id": p.get("id"),
                        "business_name": display_name,
                        "category": cat_name,
                        "full_address": p.get("formattedAddress"),
                        "phone_number": norm_phone or raw_phone,
                        "website_url": p.get("websiteUri"),
                        "maps_url": p.get("googleMapsUri"),
                        "rating": p.get("rating"),
                        "review_count": p.get("userRatingCount", 0),
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "is_demo": False
                    })
                return formatted, 1, None
            else:
                data = resp.json()
                msg = data.get("error", {}).get("message") or f"HTTP {resp.status_code}"
                return [], 1, msg
        except Exception as e:
            return [], 0, str(e)

    def _search_places_legacy(
        self,
        query: str,
        max_results: int,
        country: str,
        key: str
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """Executes search using Classic Google Places API endpoints."""
        api_calls = 0
        all_places = []
        next_page_token = None
        full_query = f"{query}, {country}" if country and country.lower() not in query.lower() else query

        try:
            while len(all_places) < max_results:
                params = {"query": full_query, "key": key}
                if next_page_token:
                    params["pagetoken"] = next_page_token
                    time.sleep(2.0)

                resp = requests.get(self.BASE_TEXT_SEARCH_URL, params=params, timeout=settings.http_timeout_seconds)
                api_calls += 1

                if resp.status_code != 200:
                    return all_places, api_calls, f"HTTP Error {resp.status_code}: {resp.text[:120]}"

                data = resp.json()
                status = data.get("status")

                if status == "ZERO_RESULTS":
                    break
                elif status == "OVER_QUERY_LIMIT":
                    return all_places, api_calls, "API Quota or Billing Limit Exceeded (OVER_QUERY_LIMIT)"
                elif status == "REQUEST_DENIED":
                    err_msg = data.get("error_message", "Request Denied by Google Places API.")
                    return all_places, api_calls, f"Google API Error: {err_msg}"
                elif status not in ("OK", "ZERO_RESULTS"):
                    err_msg = data.get("error_message", status)
                    return all_places, api_calls, f"Google API Error: {err_msg}"

                results = data.get("results", [])
                for item in results:
                    place_id = item.get("place_id")
                    detail, calls = self.get_place_details(place_id)
                    api_calls += calls
                    all_places.append(detail)
                    if len(all_places) >= max_results:
                        break

                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break

            return all_places, api_calls, None
        except Exception as e:
            return all_places, api_calls, str(e)

    def get_place_details(self, place_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Retrieves place details using supported fields:
        name, formatted_address, formatted_phone_number, website, url, rating, user_ratings_total, geometry, types
        """
        if not place_id or not self.is_configured():
            return {}, 0

        fields = [
            "place_id", "name", "formatted_address", "formatted_phone_number",
            "international_phone_number", "website", "url", "rating",
            "user_ratings_total", "geometry", "types"
        ]
        params = {
            "place_id": place_id,
            "fields": ",".join(fields),
            "key": self.api_key
        }

        try:
            resp = requests.get(self.BASE_DETAILS_URL, params=params, timeout=settings.http_timeout_seconds)
            if resp.status_code == 200:
                data = resp.json()
                res = data.get("result", {})
                
                raw_phone = res.get("formatted_phone_number") or res.get("international_phone_number")
                norm_phone, _, _ = normalize_phone_number(raw_phone, default_region="IN")

                geom = res.get("geometry", {}).get("location", {})
                types_list = res.get("types", [])
                primary_category = types_list[0].replace("_", " ").title() if types_list else "Business"

                return {
                    "place_id": res.get("place_id"),
                    "business_name": res.get("name"),
                    "category": primary_category,
                    "full_address": res.get("formatted_address"),
                    "phone_number": norm_phone or raw_phone,
                    "website_url": res.get("website"),
                    "maps_url": res.get("url"),
                    "rating": res.get("rating"),
                    "review_count": res.get("user_ratings_total", 0),
                    "latitude": geom.get("lat"),
                    "longitude": geom.get("lng"),
                    "is_demo": False
                }, 1
        except Exception as e:
            logger.error("Error retrieving place details for %s: %s", place_id, str(e))

        return {}, 1

    def _generate_mock_places(self, query: str, max_results: int, country: str) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """
        Generates realistic, clearly labeled simulated test records for demo mode.
        Marks `is_demo=True` so user interface and reports explicitly disclose simulated status.
        """
        # Determine city and category from query
        q_lower = query.lower()
        city = "Bengaluru"
        if "mumbai" in q_lower:
            city = "Mumbai"
        elif "delhi" in q_lower or "ncr" in q_lower:
            city = "Delhi"
        elif "pune" in q_lower:
            city = "Pune"
        elif "hyderabad" in q_lower:
            city = "Hyderabad"
        elif "chennai" in q_lower:
            city = "Chennai"

        category = "Dental Clinic"
        if "salon" in q_lower or "barber" in q_lower:
            category = "Beauty Salon"
        elif "restaurant" in q_lower or "cafe" in q_lower:
            category = "Restaurant & Cafe"
        elif "gym" in q_lower or "fitness" in q_lower:
            category = "Fitness Studio"
        elif "hotel" in q_lower:
            category = "Hotel & Suites"
        elif "coaching" in q_lower:
            category = "Coaching Institute"
        elif "repair" in q_lower or "auto" in q_lower:
            category = "Auto Repair Shop"

        mock_templates = [
            # High Priority: No website, valid phone, high reviews
            {
                "name": f"Arogya {category}",
                "area": "Indiranagar",
                "phone": "+91 98450 12345",
                "website": None,
                "rating": 4.6,
                "reviews": 48,
                "email": "contact@arogyacare.example.org"
            },
            {
                "name": f"Prime Care {category}",
                "area": "Koramangala",
                "phone": "+91 98200 54321",
                "website": None,
                "rating": 4.3,
                "reviews": 32,
                "email": None
            },
            # Social media only
            {
                "name": f"Urban Glow {category}",
                "area": "HSR Layout",
                "phone": "+91 97400 98765",
                "website": "https://www.instagram.com/urbanglow_official",
                "rating": 4.7,
                "reviews": 65,
                "email": "info@urbanglow.example.org"
            },
            # Directory listing only
            {
                "name": f"Apex {category} Services",
                "area": "Whitefield",
                "phone": "+91 80 4123 4567",
                "website": "https://www.justdial.com/Bengaluru/Apex-Services",
                "rating": 4.1,
                "reviews": 19,
                "email": None
            },
            # Unverified / No website found
            {
                "name": f"Shree Krishna {category}",
                "area": "Jayanagar",
                "phone": "+91 99000 11223",
                "website": None,
                "rating": 4.5,
                "reviews": 24,
                "email": None
            },
            # Has independent website (should be filtered or scored 0)
            {
                "name": f"Global Elite {category}",
                "area": "MG Road",
                "phone": "+91 80 2558 7890",
                "website": "https://www.globalelitecare.org",
                "rating": 4.8,
                "reviews": 112,
                "email": "hello@globalelitecare.org"
            },
            # Moderate activity, no website
            {
                "name": f"Sunrise {category}",
                "area": "BTM Layout",
                "phone": "+91 94480 33445",
                "website": None,
                "rating": 3.9,
                "reviews": 8,
                "email": None
            },
            # New business, no website, no reviews
            {
                "name": f"New Era {category}",
                "area": "Electronic City",
                "phone": "+91 96110 88776",
                "website": None,
                "rating": 0.0,
                "reviews": 0,
                "email": None
            }
        ]

        count = min(max_results, len(mock_templates))
        results = []
        for i in range(count):
            tpl = mock_templates[i]
            addr = f"{tpl['area']}, {city}, Karnataka, {country}"
            p_id = f"mock_place_id_{city.lower()}_{i+1}"
            norm_phone, _, _ = normalize_phone_number(tpl["phone"], "IN")

            results.append({
                "place_id": p_id,
                "business_name": tpl["name"],
                "category": category,
                "full_address": addr,
                "area": tpl["area"],
                "city": city,
                "state": "Karnataka",
                "country": country,
                "phone_number": norm_phone or tpl["phone"],
                "website_url": tpl["website"],
                "maps_url": f"https://maps.google.com/?q={p_id}",
                "rating": tpl["rating"],
                "review_count": tpl["reviews"],
                "latitude": 12.9716 + (i * 0.01),
                "longitude": 77.5946 + (i * 0.01),
                "email": tpl["email"],
                "is_demo": True
            })

        return results, 1, None


google_places_service = GooglePlacesService()

