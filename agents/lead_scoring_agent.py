from typing import List, Dict, Any, Tuple
from services.scoring_service import scoring_service
from config.logging_config import logger


class LeadScoringAgent:
    """Agent 5: Evaluates and scores prospects between 0 and 100."""

    def __init__(self, scorer=scoring_service):
        self.scorer = scorer

    def run(
        self,
        records: List[Dict[str, Any]],
        min_score: float = 0.0,
        exclude_existing_websites: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Scores all records and separates qualified leads from low-scoring records.
        Returns:
            (qualified_leads, all_scored_records)
        """
        scored_all = []
        qualified = []

        for rec in records:
            r = dict(rec)
            score, priority, explanation = self.scorer.calculate_lead_score(r)
            r["lead_score"] = score
            r["priority"] = priority
            r["scoring_explanation"] = explanation

            scored_all.append(r)

            # Filtering
            if exclude_existing_websites and r.get("website_status") in ("WEBSITE_FOUND", "WEBSITE_FOUND_ACCESSIBLE"):
                continue

            if score >= min_score:
                qualified.append(r)

        # Sort by score descending
        qualified.sort(key=lambda x: x.get("lead_score", 0.0), reverse=True)
        scored_all.sort(key=lambda x: x.get("lead_score", 0.0), reverse=True)

        logger.info("LeadScoringAgent scored %d leads: %d qualified (min score: %.1f)",
                    len(records), len(qualified), min_score)

        return qualified, scored_all


lead_scoring_agent = LeadScoringAgent()

