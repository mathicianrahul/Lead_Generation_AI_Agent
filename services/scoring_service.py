from typing import Dict, Any, Tuple
from config.settings import ScoringWeights, settings

# High value categories for web development services
HIGH_VALUE_CATEGORIES = {
    "dental clinic", "dentist", "healthcare", "hospital", "clinic",
    "hotel", "resort", "guest house", "restaurant", "cafe", "bistro",
    "real estate", "property consultant", "coaching", "training center",
    "gym", "fitness center", "yoga studio", "salon", "beauty parlour", "spa"
}

MEDIUM_VALUE_CATEGORIES = {
    "retail", "boutique", "automobile repair", "car service", "bike service",
    "travel agency", "tour operator", "consultant", "lawyer", "advocate",
    "chartered accountant", "architect", "interior designer", "plumber", "electrician"
}


class ScoringService:
    def __init__(self, weights: ScoringWeights = settings.scoring_weights):
        self.weights = weights

    def calculate_lead_score(self, lead_data: Dict[str, Any]) -> Tuple[float, str, str]:
        """
        Calculates a deterministic qualification score between 0 and 100.
        Returns:
            (score, priority, explanation)
        """
        breakdown = []
        total_score = 0.0

        # A. Website Opportunity (max: weights.website_opportunity, default 40)
        web_status = (lead_data.get("website_status") or "UNVERIFIED").upper()
        web_score = 0.0
        if web_status == "NO_WEBSITE_FOUND":
            web_score = self.weights.website_opportunity * 1.0  # 40 pts
            breakdown.append(f"+{web_score:.0f} pts: No independent business website found")
        elif web_status == "SOCIAL_MEDIA_ONLY":
            web_score = self.weights.website_opportunity * 0.875  # 35 pts
            breakdown.append(f"+{web_score:.0f} pts: Only social media presence detected")
        elif web_status == "DIRECTORY_ONLY":
            web_score = self.weights.website_opportunity * 0.75  # 30 pts
            breakdown.append(f"+{web_score:.0f} pts: Only third-party directory/map listing found")
        elif web_status == "UNVERIFIED":
            web_score = self.weights.website_opportunity * 0.375  # 15 pts
            breakdown.append(f"+{web_score:.0f} pts: Website status unverified")
        elif web_status == "CHECK_FAILED":
            web_score = self.weights.website_opportunity * 0.25  # 10 pts
            breakdown.append(f"+{web_score:.0f} pts: Website check encountered technical failure")
        elif web_status in ("WEBSITE_FOUND", "WEBSITE_FOUND_ACCESSIBLE"):
            web_score = 0.0
            breakdown.append("+0 pts: Confirmed independent website already exists")
        else:
            web_score = 0.0
        total_score += web_score

        # B. Public Business Phone Available (max: weights.phone_available, default 15)
        phone = lead_data.get("phone_number")
        phone_score = 0.0
        if phone and str(phone).strip():
            phone_score = self.weights.phone_available
            breakdown.append(f"+{phone_score:.0f} pts: Valid public business phone available ({phone})")
        else:
            breakdown.append("+0 pts: No public phone number listed")
        total_score += phone_score

        # C. Public Business Email Available (max: weights.email_available, default 15)
        email = lead_data.get("email") or lead_data.get("email_address")
        email_score = 0.0
        if email and str(email).strip():
            email_score = self.weights.email_available
            breakdown.append(f"+{email_score:.0f} pts: Verified public business email available")
        else:
            breakdown.append("+0 pts: No public email address found")
        total_score += email_score

        # D. Evidence of Active Operations (max: weights.active_operations, default 15)
        review_count = lead_data.get("review_count") or 0
        rating = lead_data.get("rating") or 0.0
        ops_score = 0.0
        if review_count >= 20 or (rating >= 4.0 and review_count >= 10):
            ops_score = self.weights.active_operations
            breakdown.append(f"+{ops_score:.0f} pts: High active operations ({review_count} reviews, {rating}★)")
        elif review_count >= 5 or rating >= 3.5:
            ops_score = self.weights.active_operations * (10.0 / 15.0)
            breakdown.append(f"+{ops_score:.0f} pts: Moderate active operations ({review_count} reviews, {rating}★)")
        elif review_count > 0:
            ops_score = self.weights.active_operations * (5.0 / 15.0)
            breakdown.append(f"+{ops_score:.0f} pts: Limited active operations ({review_count} review)")
        else:
            breakdown.append("+0 pts: No public customer reviews recorded")
        total_score += ops_score

        # E. Potential Website Value for Category (max: weights.category_website_value, default 15)
        category = (lead_data.get("category") or "").lower()
        cat_score = 0.0
        is_high = any(c in category for c in HIGH_VALUE_CATEGORIES)
        is_med = any(c in category for c in MEDIUM_VALUE_CATEGORIES)

        if is_high:
            cat_score = self.weights.category_website_value
            breakdown.append(f"+{cat_score:.0f} pts: High commercial value for website in '{category}'")
        elif is_med:
            cat_score = self.weights.category_website_value * (10.0 / 15.0)
            breakdown.append(f"+{cat_score:.0f} pts: Moderate commercial value for website in '{category}'")
        else:
            cat_score = self.weights.category_website_value * (5.0 / 15.0)
            breakdown.append(f"+{cat_score:.0f} pts: Standard commercial website value")
        total_score += cat_score

        # Round and cap
        final_score = round(min(100.0, max(0.0, total_score)), 1)

        # Priority bands
        if final_score >= 80.0:
            priority = "High"
        elif final_score >= 60.0:
            priority = "Medium"
        else:
            priority = "Low"

        explanation = "; ".join(breakdown)
        return final_score, priority, explanation


scoring_service = ScoringService()

