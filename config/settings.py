import os
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")


class ScoringWeights(BaseModel):
    """Configurable scoring weights for lead qualification (total 100 points)."""
    website_opportunity: float = 40.0
    phone_available: float = 15.0
    email_available: float = 15.0
    active_operations: float = 15.0
    category_website_value: float = 15.0


class Settings(BaseModel):
    """Application configuration settings."""
    app_name: str = "LeadPilot AI"
    app_version: str = "1.0.0"
    app_env: str = os.getenv("APP_ENV", "development")
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

    # Database
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'leadpilot.db'}")

    # Google Maps Places API
    google_maps_api_key: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY")

    # LLM Provider
    llm_provider: str = os.getenv("LLM_PROVIDER", "huggingface")
    huggingface_api_token: Optional[str] = os.getenv("HUGGINGFACE_API_TOKEN")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")

    # Gmail OAuth
    google_client_id: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    gmail_credentials_file: str = os.getenv("GMAIL_CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
    gmail_token_file: str = os.getenv("GMAIL_TOKEN_FILE", str(BASE_DIR / "token.json"))

    # Operational safety limits
    max_daily_emails: int = int(os.getenv("MAX_DAILY_EMAILS", "10"))
    max_search_results: int = int(os.getenv("MAX_SEARCH_RESULTS", "100"))
    default_min_lead_score: int = int(os.getenv("DEFAULT_MIN_LEAD_SCORE", "60"))
    http_timeout_seconds: int = int(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    max_redirects: int = 3

    # Scoring weights
    scoring_weights: ScoringWeights = ScoringWeights()

    # Paths
    base_dir: Path = BASE_DIR
    exports_dir: Path = BASE_DIR / "exports"

    def has_google_maps_key(self) -> bool:
        return bool(self.google_maps_api_key and self.google_maps_api_key.strip() and not self.google_maps_api_key.startswith("your_"))

    def has_llm_key(self) -> bool:
        if self.llm_provider == "huggingface":
            return bool(self.huggingface_api_token and self.huggingface_api_token.strip())
        elif self.llm_provider == "openai":
            return bool(self.openai_api_key and self.openai_api_key.strip())
        return False

    def has_gmail_config(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret) or os.path.exists(self.gmail_credentials_file)


# Singleton instance
settings = Settings()

