import os
import json
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    APPLICATIONS_DIR: Path = BASE_DIR / "applications"
    DB_PATH: Path = BASE_DIR / "data" / "job_hunter.db"

    # AI Brain (Zero-cost Free Tiers)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Candidate details
    CANDIDATE_NAME: str = os.getenv("CANDIDATE_NAME", "Muhammad Bilal")
    CANDIDATE_EMAIL: str = os.getenv("CANDIDATE_EMAIL", "candidate@example.com")
    CANDIDATE_PHONE: str = os.getenv("CANDIDATE_PHONE", "+92-300-1234567")
    CANDIDATE_LOCATION: str = os.getenv("CANDIDATE_LOCATION", "Worldwide Remote")
    CANDIDATE_LINKEDIN: str = os.getenv("CANDIDATE_LINKEDIN", "")
    CANDIDATE_GITHUB: str = os.getenv("CANDIDATE_GITHUB", "")
    CANDIDATE_PORTFOLIO: str = os.getenv("CANDIDATE_PORTFOLIO", "")

    # Matching & Search Preferences
    MATCH_THRESHOLD: int = int(os.getenv("MATCH_THRESHOLD", "75"))
    TARGET_ROLES_RAW: str = os.getenv("TARGET_ROLES", "Full-Stack Developer, Frontend Engineer, Mobile App Developer")
    TARGET_LOCATIONS_RAW: str = os.getenv("TARGET_LOCATIONS", "Worldwide Remote, United States, Canada, United Kingdom, Europe, UAE, Australia")
    MIN_SALARY_USD: int = int(os.getenv("MIN_SALARY_USD", "0"))

    # Strict Freshness & Autonomous Auto-Pilot
    MAX_JOB_AGE_HOURS: int = int(os.getenv("MAX_JOB_AGE_HOURS", "24")) # Strictly under 24 hours
    AUTO_PILOT_ENABLED: bool = os.getenv("AUTO_PILOT_ENABLED", "true").lower() in ("true", "1", "yes")
    AUTO_PILOT_INTERVAL_MINUTES: int = int(os.getenv("AUTO_PILOT_INTERVAL_MINUTES", "60"))
    AUTO_APPLY_ENABLED: bool = os.getenv("AUTO_APPLY_ENABLED", "true").lower() in ("true", "1", "yes")
    AUTO_APPLY_MIN_SCORE: int = int(os.getenv("AUTO_APPLY_MIN_SCORE", "75"))

    # Gmail SMTP & IMAP
    GMAIL_USER: str = os.getenv("GMAIL_USER", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    NOTIFY_EMAIL: str = os.getenv("NOTIFY_EMAIL", "")
    ENABLE_EMAIL_DIGEST: bool = os.getenv("ENABLE_EMAIL_DIGEST", "false").lower() in ("true", "1", "yes")
    ENABLE_RECRUITER_TRACKER: bool = os.getenv("ENABLE_RECRUITER_TRACKER", "false").lower() in ("true", "1", "yes")
    DAILY_DIGEST_TIME: str = os.getenv("DAILY_DIGEST_TIME", "09:00")

    # Web Dashboard
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    @property
    def target_roles(self) -> List[str]:
        return [r.strip() for r in self.TARGET_ROLES_RAW.split(",") if r.strip()]

    @property
    def target_locations(self) -> List[str]:
        return [loc.strip() for loc in self.TARGET_LOCATIONS_RAW.split(",") if loc.strip()]

    def get_profile(self) -> dict:
        profile_path = self.BASE_DIR / "config" / "my_profile.json"
        if profile_path.exists():
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "name": self.CANDIDATE_NAME,
            "title": "Full-Stack & Mobile App Engineer",
            "contact": {
                "email": self.CANDIDATE_EMAIL,
                "phone": self.CANDIDATE_PHONE,
                "location": self.CANDIDATE_LOCATION,
                "linkedin": self.CANDIDATE_LINKEDIN,
                "github": self.CANDIDATE_GITHUB,
                "portfolio": self.CANDIDATE_PORTFOLIO
            }
        }

    def get_master_cv(self) -> str:
        cv_path = self.DATA_DIR / "master_cv.txt"
        if cv_path.exists():
            try:
                with open(cv_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return "Muhammad Bilal - Senior Full-Stack & Mobile Engineer"

settings = Settings()

# Ensure required directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
