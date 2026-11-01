"""
LeadPilot AI — Common Discovery Provider Abstraction
Defines the standard interface and common normalization for business discovery providers
(Google Places API, OpenStreetMap Overpass API).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple


class DiscoveryProvider(ABC):
    """Abstract Base Class for Business Discovery Providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the discovery provider."""
        pass

    @property
    @abstractmethod
    def attribution(self) -> str:
        """Mandatory attribution string for data licensing (e.g., OpenStreetMap ODbL)."""
        pass

    @abstractmethod
    def search_places(
        self,
        query: str,
        location: str = "",
        area: str = "",
        country: str = "India",
        max_results: int = 20
    ) -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        """
        Executes discovery search.
        Returns:
            Tuple of:
            - list of normalized lead dicts
            - total API calls made
            - optional error message
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Checks if provider has required credentials or configuration."""
        pass


def normalize_discovery_record(
    place_id: str,
    business_name: str,
    category: Optional[str] = None,
    full_address: Optional[str] = None,
    area: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: str = "India",
    phone_number: Optional[str] = None,
    email: Optional[str] = None,
    website_url: Optional[str] = None,
    maps_url: Optional[str] = None,
    rating: Optional[float] = None,
    review_count: int = 0,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    source: str = "Google Places API",
    attribution: str = "",
    website_status: str = "UNVERIFIED",
    is_demo: bool = False
) -> Dict[str, Any]:
    """
    Constructs a uniform lead dictionary across all discovery providers.
    Guarantees consistent keys and types across Google Places and OpenStreetMap.
    """
    clean_name = (business_name or "Unknown Business").strip()
    return {
        "place_id": str(place_id).strip() if place_id else None,
        "business_name": clean_name,
        "category": (category or "Local Business").strip().title(),
        "full_address": (full_address or "").strip() or None,
        "area": (area or "").strip() or None,
        "city": (city or "").strip().title() or None,
        "state": (state or "").strip().title() or None,
        "country": (country or "India").strip().title(),
        "phone_number": str(phone_number).strip() if phone_number else None,
        "email": str(email).strip().lower() if email else None,
        "website_url": str(website_url).strip() if website_url else None,
        "maps_url": str(maps_url).strip() if maps_url else None,
        "rating": float(rating) if rating is not None else None,
        "review_count": int(review_count) if review_count else 0,
        "latitude": float(latitude) if latitude is not None else None,
        "longitude": float(longitude) if longitude is not None else None,
        "website_status": website_status,
        "source": source,
        "attribution": attribution,
        "is_demo": bool(is_demo)
    }

