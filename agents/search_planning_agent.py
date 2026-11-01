import uuid
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from config.logging_config import logger


class SearchPlanInput(BaseModel):
    country: str = "India"
    state: str = ""
    city: str
    area: str = ""
    category: str
    keywords: str = ""
    max_results: int = 20
    min_score: float = 60.0
    require_phone: bool = False
    require_email: bool = False
    enable_verification: bool = True
    enable_ai_personalization: bool = True
    budget_limit: int = 50


class SearchPlanOutput(BaseModel):
    job_id: str
    normalized_params: Dict[str, Any]
    queries: List[str]
    estimated_api_calls: int
    budget_warning: bool
    status: str


class SearchPlanningAgent:
    """Agent 1: Validates search inputs and constructs an executable query plan."""

    def run(self, plan_input: SearchPlanInput) -> SearchPlanOutput:
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        city_clean = plan_input.city.strip().title()
        area_clean = plan_input.area.strip().title()
        category_clean = plan_input.category.strip().title()
        country_clean = plan_input.country.strip().title()

        queries = []
        # Query 1: Targeted area + category
        if area_clean:
            queries.append(f"{category_clean} in {area_clean}, {city_clean}")
        # Query 2: Broader city + category
        queries.append(f"{category_clean} in {city_clean}")

        # Query 3: Custom keywords if provided
        if plan_input.keywords.strip():
            queries.append(f"{plan_input.keywords.strip()} in {city_clean}")

        # Remove duplicate queries
        unique_queries = list(dict.fromkeys(queries))

        # Estimate API operations: roughly 1 text search + details per expected result
        estimated_calls = min(plan_input.max_results + len(unique_queries), plan_input.budget_limit)
        budget_warning = estimated_calls >= plan_input.budget_limit

        normalized_params = {
            "country": country_clean,
            "state": plan_input.state.strip().title(),
            "city": city_clean,
            "area": area_clean,
            "category": category_clean,
            "keywords": plan_input.keywords.strip(),
            "max_results": plan_input.max_results,
            "min_score": plan_input.min_score,
            "require_phone": plan_input.require_phone,
            "require_email": plan_input.require_email,
            "enable_verification": plan_input.enable_verification,
            "enable_ai_personalization": plan_input.enable_ai_personalization,
            "budget_limit": plan_input.budget_limit
        }

        logger.info("SearchPlanningAgent generated job %s with %d queries for %s in %s",
                    job_id, len(unique_queries), category_clean, city_clean)

        return SearchPlanOutput(
            job_id=job_id,
            normalized_params=normalized_params,
            queries=unique_queries,
            estimated_api_calls=estimated_calls,
            budget_warning=budget_warning,
            status="PLANNED"
        )


search_planning_agent = SearchPlanningAgent()

