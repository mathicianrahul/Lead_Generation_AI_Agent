"""
LeadPilot AI — OpenStreetMap Overpass API Discovery Service
Provides free, open-access business discovery using OpenStreetMap Overpass QL queries.
Includes category mapping, safe tag extraction, rate limiting, and caching.
"""
import time
import re
from typing import Dict, Any, List, Optional, Tuple
import requests

from config.settings import settings
from config.logging_config import logger
from services.discovery_provider import DiscoveryProvider, normalize_discovery_record
from utils.phone_utils import normalize_phone_number

# Category mapping from common search terms to OSM key/value pairs
OSM_CATEGORY_TAGS = {
    # Medical & Healthcare
    "dental clinic": '["amenity"="dentist"]',
    "dentist": '["amenity"="dentist"]',
    "dental": '["amenity"="dentist"]',
    "clinic": '["amenity"~"clinic|doctors"]',
    "doctor": '["amenity"="doctors"]',
    "hospital": '["amenity"="hospital"]',
    "pharmacy": '["amenity"="pharmacy"]',
    "chemist": '["amenity"="pharmacy"]',
    "optician": '["shop"="optician"]',
    "veterinary": '["amenity"="veterinary"]',

    # Food & Hospitality
    "restaurant": '["amenity"="restaurant"]',
    "cafe": '["amenity"="cafe"]',
    "coffee": '["amenity"="cafe"]',
    "bakery": '["shop"="bakery"]',
    "bar": '["amenity"="bar"]',
    "pub": '["amenity"="pub"]',
    "fast food": '["amenity"="fast_food"]',
    "hotel": '["tourism"="hotel"]',
    "guest house": '["tourism"="guest_house"]',
    "hostel": '["tourism"="hostel"]',

    # Beauty, Wellness & Fitness
    "salon": '["shop"~"hairdresser|beauty"]',
    "hair salon": '["shop"="hairdresser"]',
    "beauty parlour": '["shop"="beauty"]',
    "spa": '["amenity"="spa"]',
    "gym": '["leisure"="fitness_centre"]',
    "fitness": '["leisure"="fitness_centre"]',
    "yoga": '["leisure"~"fitness_centre|dance"]',

    # Professional & Business Services
    "lawyer": '["office"="lawyer"]',
    "advocate": '["office"="lawyer"]',
    "accountant": '["office"="accountant"]',
    "chartered accountant": '["office"="accountant"]',
    "real estate": '["office"="estate_agent"]',
    "property consultant": '["office"="estate_agent"]',
    "travel agency": '["shop"="travel_agency"]',
    "insurance": '["office"="insurance"]',
    "architect": '["office"="architect"]',
    "interior designer": '["office"="interior_design"]',

    # Automotive & Retail
    "car repair": '["shop"="car_repair"]',
    "car service": '["shop"="car_repair"]',
    "auto repair": '["shop"="car_repair"]',
    "supermarket": '["shop"="supermarket"]',
    "grocery": '["shop"~"supermarket|convenience"]',
    "boutique": '["shop"="clothes"]',
    "clothing": '["shop"="clothes"]',
    "electronics": '["shop"="electronics"]',
    "jeweller": '["shop"="jewelry"]',
    "jewelry": '["shop"="jewelry"]',
}


class OpenStreetMapService(DiscoveryProvider):
    """
    OpenStreetMap Overpass API integration service.
    Implements rate limiting, caching, safe tag extraction, and error handling.
    """
    ATTRIBUTION = "Data © OpenStreetMap contributors (ODbL)"

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        timeout: Optional[int] = None,
        rate_limit_delay: Optional[float] = None
    ):
        self.endpoint_url = endpoint_url or settings.overpass_api_url
        self.timeout = timeout or settings.overpass_timeout_seconds
        self.rate_limit_delay = rate_limit_delay or settings.overpass_rate_limit_delay

        # Rate limiting state
        self._last_request_time: float = 0.0

        # In-memory query cache: query_key -> (timestamp, records)
        self._cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._cache_ttl_seconds: float = 600.0  # 10 minutes cache

    @property
    def provider_name(self) -> str:
        return "OpenStreetMap"

    @property
    def attribution(self) -> str:
        return self.ATTRIBUTION

    def is_configured(self) -> bool:
        """OpenStreetMap Overpass API is a free public service and requires no API key."""
        return bool(self.endpoint_url and self.endpoint_url.strip())

    def _enforce_rate_limit(self):
        """Enforces a pause between live requests to respect Overpass public server guidelines."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def _build_osm_filter(self, category: str) -> str:
        """Maps a business query or category to an Overpass QL tag filter."""
        clean = (category or "").strip().lower()
        if clean in OSM_CATEGORY_TAGS:
            return OSM_CATEGORY_TAGS[clean]

        # Partial matching in category map
        for key, tag in OSM_CATEGORY_TAGS.items():
            if key in clean or clean in key:
                return tag

        # Regex tag fallback for common commercial amenity/shop/office keys
        safe_val = re.sub(r'[^a-zA-Z0-9_]', '', clean.replace(' ', '_'))
        if safe_val:
            return f'["amenity"~"^{safe_val}$",i]'
        return '["amenity"]'

    def _build_overpass_query(
        self,
        category: str,
        city: str,
        area: str = "",
        max_results: int = 20,
        timeout_sec: int = 25
    ) -> str:
        """Constructs an Overpass QL query string with area boundaries."""
        osm_filter = self._build_osm_filter(category)
        clean_city = re.sub(r'[\'"\\]', '', city.strip())
        clean_area = re.sub(r'[\'"\\]', '', area.strip()) if area else ""

        # Area definitions
        area_clauses = []
        if clean_city:
            area_clauses.append(f'area["name"~"^{re.escape(clean_city)}$",i]->.cityArea;')
            area_clauses.append(f'area["name:en"~"^{re.escape(clean_city)}$",i]->.cityArea;')
        if clean_area:
            area_clauses.append(f'area["name"~"^{re.escape(clean_area)}$",i]->.suburbArea;')

        target_area = ".suburbArea" if clean_area else ".cityArea"

        # Overpass QL query
        query = f"""
[out:json][timeout:{timeout_sec}];
(
  {''.join(area_clauses)}
);
(
  node{osm_filter}(area{target_area});
  way{osm_filter}(area{target_area});
);
out center {max_results};
"""
        return query.strip()

    def search_places(
        self,
        query: str,
        location: str = "",
        area: str = "",
        country: str = "India",
        max_results: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """
        Queries OpenStreetMap Overpass API for businesses matching the category and location.
        Returns:
            (records_list, api_calls_made, error_message_if_any)
        """
        # Determine city vs query
        city = location or ""
        category = query
        # If query contains "in", split e.g. "Dental Clinic in Mumbai"
        if " in " in query.lower() and not city:
            parts = query.lower().split(" in ", 1)
            category = parts[0].strip()
            city = parts[1].strip()

        # Cache check
        cache_key = f"{category.lower()}:{city.lower()}:{area.lower()}:{country.lower()}:{max_results}"
        now = time.time()
        if cache_key in self._cache:
            ts, cached_records = self._cache[cache_key]
            if now - ts < self._cache_ttl_seconds:
                logger.info("OpenStreetMapService returning %d cached records for '%s' in '%s'",
                            len(cached_records), category, city)
                return cached_records, 0, None

        # Build Overpass QL
        overpass_ql = self._build_overpass_query(
            category=category,
            city=city,
            area=area,
            max_results=max_results,
            timeout_sec=self.timeout
        )

        self._enforce_rate_limit()

        headers = {
            "User-Agent": "LeadPilotAI/1.0 (https://github.com/mathicianrahul/Lead_Generation_AI_Agent)",
            "Accept": "application/json"
        }

        try:
            resp = requests.post(
                self.endpoint_url,
                data={"data": overpass_ql},
                headers=headers,
                timeout=self.timeout + 5
            )

            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                if not elements:
                    return [], 1, "ZERO_RESULTS"

                formatted_records = []
                for el in elements:
                    rec = self._parse_element(el, category, city, area, country)
                    if rec:
                        formatted_records.append(rec)
                        if len(formatted_records) >= max_results:
                            break

                # Save to cache
                self._cache[cache_key] = (now, formatted_records)
                logger.info("OpenStreetMapService discovered %d leads for '%s' in '%s'",
                            len(formatted_records), category, city)
                return formatted_records, 1, None

            elif resp.status_code == 429:
                err_msg = "Overpass API rate limit reached (HTTP 429). Public servers are throttled."
                logger.warning(err_msg)
                return [], 1, err_msg
            elif resp.status_code in (504, 502, 503):
                err_msg = f"Overpass API server busy/timeout (HTTP {resp.status_code})."
                logger.warning(err_msg)
                return [], 1, err_msg
            else:
                err_msg = f"Overpass API error HTTP {resp.status_code}: {resp.text[:120]}"
                logger.warning(err_msg)
                return [], 1, err_msg

        except requests.exceptions.Timeout:
            err_msg = f"Overpass API timed out after {self.timeout}s."
            logger.warning(err_msg)
            return [], 0, err_msg
        except requests.exceptions.RequestException as e:
            err_msg = f"Overpass API network error: {str(e)}"
            logger.warning(err_msg)
            return [], 0, err_msg
        except Exception as e:
            err_msg = f"Overpass API unexpected error: {str(e)}"
            logger.error(err_msg)
            return [], 0, err_msg

    def _parse_element(
        self,
        el: Dict[str, Any],
        fallback_category: str,
        city: str,
        area: str,
        country: str
    ) -> Optional[Dict[str, Any]]:
        """Safely parses an OpenStreetMap element into a normalized lead record."""
        tags = el.get("tags") or {}

        # 1. Business Name
        name = (
            tags.get("name")
            or tags.get("name:en")
            or tags.get("official_name")
            or tags.get("operator")
            or tags.get("brand")
        )
        if not name:
            # Fallback to category representation if named element has no specific title
            cat_name = tags.get("amenity") or tags.get("shop") or tags.get("office") or fallback_category
            name = f"{cat_name.title()} Business"

        # 2. Coordinates
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            center = el.get("center") or {}
            lat = center.get("lat")
            lon = center.get("lon")

        # 3. Category
        cat = (
            tags.get("amenity")
            or tags.get("shop")
            or tags.get("office")
            or tags.get("tourism")
            or tags.get("healthcare")
            or fallback_category
        ).replace("_", " ").title()

        # 4. Contact Phone
        raw_phone = (
            tags.get("phone")
            or tags.get("contact:phone")
            or tags.get("contact:mobile")
            or tags.get("mobile")
        )
        norm_phone = None
        if raw_phone:
            country_code = "IN" if country.lower() == "india" else "US"
            norm_phone, _, _ = normalize_phone_number(raw_phone, country_code)
            if not norm_phone:
                norm_phone = raw_phone

        # 5. Email
        raw_email = tags.get("email") or tags.get("contact:email")

        # 6. Website
        # IMPORTANT: Do not assume a missing website tag means the business definitely has no website.
        raw_website = (
            tags.get("website")
            or tags.get("contact:website")
            or tags.get("url")
        )

        # 7. Address Assembly
        addr_parts = []
        if tags.get("addr:housenumber"):
            addr_parts.append(tags["addr:housenumber"])
        if tags.get("addr:street"):
            addr_parts.append(tags["addr:street"])
        suburb = tags.get("addr:suburb") or tags.get("addr:neighbourhood") or area
        if suburb:
            addr_parts.append(suburb)
        addr_city = tags.get("addr:city") or city
        if addr_city:
            addr_parts.append(addr_city)
        if tags.get("addr:state"):
            addr_parts.append(tags["addr:state"])
        if tags.get("addr:postcode"):
            addr_parts.append(tags["addr:postcode"])

        full_addr = ", ".join([p for p in addr_parts if p.strip()]) if addr_parts else f"{city}, {country}"

        # 8. Unique Place ID & Maps URL
        el_type = el.get("type", "node")
        el_id = el.get("id")
        place_id = f"osm:{el_type}:{el_id}"
        maps_url = f"https://www.openstreetmap.org/{el_type}/{el_id}"

        # 9. Website Status
        # If website tag is present, label as UNVERIFIED pending verification check.
        # If website tag is absent, STILL label as UNVERIFIED because OSM is crowdsourced.
        website_status = "UNVERIFIED"

        return normalize_discovery_record(
            place_id=place_id,
            business_name=name,
            category=cat,
            full_address=full_addr,
            area=suburb or None,
            city=addr_city or None,
            state=tags.get("addr:state"),
            country=country,
            phone_number=norm_phone,
            email=raw_email,
            website_url=raw_website,
            maps_url=maps_url,
            rating=None,  # OpenStreetMap does not have star ratings
            review_count=0,
            latitude=lat,
            longitude=lon,
            source="OpenStreetMap",
            attribution=self.ATTRIBUTION,
            website_status=website_status,
            is_demo=False
        )

    def _generate_mock_osm_places(
        self,
        query: str,
        city: str,
        max_results: int = 5,
        country: str = "India"
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """Generates realistic mock OSM discovery records for testing/offline scenarios."""
        mock_records = []
        category = query.replace(" in " + city, "") if city else query
        for i in range(1, max_results + 1):
            mock_records.append(normalize_discovery_record(
                place_id=f"osm:node:mock_{i}_{int(time.time())}",
                business_name=f"{category.title()} Hub {i}",
                category=category.title(),
                full_address=f"Plot #{i * 12}, Main Road, {city or 'Bengaluru'}, {country}",
                area=f"Sector {i}",
                city=city or "Bengaluru",
                state="Karnataka" if country.lower() == "india" else None,
                country=country,
                phone_number=f"+9180{i:04d}{i:04d}",
                email=f"contact{i}@osmhub{i}.example.com" if i % 2 == 0 else None,
                website_url=f"https://www.osmhub{i}.example.com" if i % 3 == 0 else None,
                maps_url=f"https://www.openstreetmap.org/node/99999{i}",
                rating=None,
                review_count=0,
                latitude=12.9716 + (i * 0.001),
                longitude=77.5946 + (i * 0.001),
                source="OpenStreetMap",
                attribution=self.ATTRIBUTION,
                website_status="UNVERIFIED",
                is_demo=True
            ))
        return mock_records, 1, None


# Singleton instance
osm_service = OpenStreetMapService()

