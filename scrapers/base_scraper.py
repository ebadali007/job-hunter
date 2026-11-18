import re
import html
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
from config.settings import settings

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        """Fetch jobs and return standardized dictionary list."""
        pass

    def clean_html(self, raw_html: str) -> str:
        """Strip HTML tags, decode entities, and normalize whitespace."""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        for script_or_style in soup(["script", "style", "header", "footer", "nav"]):
            script_or_style.decompose()
        text = soup.get_text(separator=" ")
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def is_role_match(self, title: str, description: str, tags: str, target_roles: List[str]) -> bool:
        """Check if job matches any of the target software engineering roles, strictly excluding non-tech roles."""
        if not target_roles:
            return True

        title_lower = title.lower()

        # Strict exclusion of non-developer / sales / commercial / legal roles
        EXCLUDED_KEYWORDS = [
            "sales", "account executive", "legal", "counsel", "recruiter", "talent acquisition",
            "marketing", "data entry", "office assistant", "copywriter", "content creator",
            "customer support", "customer service", "receptionist", "financial analyst", "accountant",
            "business development", "bdr", "sdr", "sales manager", "commercial lead"
        ]
        if any(bad in title_lower for bad in EXCLUDED_KEYWORDS):
            return False

        combined = f"{title} {tags} {description[:1200]}".lower()
        combined_norm = combined.replace("-", " ").replace("_", " ")

        for role in target_roles:
            role_lower = role.lower()
            role_norm = role_lower.replace("-", " ").replace("_", " ")

            # Direct substring match
            if role_lower in combined or role_norm in combined_norm:
                return True

            # Semantic developer/engineer interchangeable matching
            core_words = [w for w in role_norm.split() if w not in ("developer", "engineer", "dev", "app", "application", "specialist", "mid", "senior", "lead")]
            if core_words and all(w in combined_norm for w in core_words):
                # Ensure it's a software/tech role
                if any(t in combined_norm for t in ("engineer", "developer", "programmer", "dev", "coder", "tech", "architect", "lead")):
                    return True

        return False

    def is_location_match(self, location: str, target_locations: List[str]) -> bool:
        """Check if location aligns with target regions or remote status."""
        if not target_locations:
            return True
        loc_lower = (location or "remote").lower()
        if "remote" in loc_lower or "anywhere" in loc_lower or "worldwide" in loc_lower or "global" in loc_lower:
            return True
        for target in target_locations:
            if target.lower() in loc_lower:
                return True
        return False

    def is_posted_under_24h(self, date_val: Any, max_hours: float = 24.0) -> Tuple[bool, float]:
        """
        Calculates job age and verifies if job was posted within max_hours (strictly under 24 hours).
        Returns (is_under_max_hours, age_hours).
        """
        if date_val is None or date_val == "":
            # If no date metadata is provided, treat as fresh (0.0 hours)
            return True, 0.0

        now_utc = datetime.now(timezone.utc)

        # Handle numeric timestamps (epoch seconds or ms)
        if isinstance(date_val, (int, float)):
            try:
                epoch = float(date_val)
                if epoch > 1e11:  # milliseconds
                    epoch = epoch / 1000.0
                dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
                age_hours = (now_utc - dt).total_seconds() / 3600.0
                return (age_hours <= max_hours, round(age_hours, 1))
            except Exception:
                return True, 0.0

        date_str = str(date_val).strip()
        lower_str = date_str.lower()

        # Handle relative date strings
        try:
            if "just now" in lower_str or "moments ago" in lower_str:
                return True, 0.1

            # Match "X hours ago", "X mins ago"
            hr_match = re.search(r'(\d+)\s*(?:hour|hr|h)', lower_str)
            if hr_match:
                hours = float(hr_match.group(1))
                return (hours <= max_hours, round(hours, 1))

            min_match = re.search(r'(\d+)\s*(?:min|minute|m)', lower_str)
            if min_match:
                hours = float(min_match.group(1)) / 60.0
                return (hours <= max_hours, round(hours, 1))

            day_match = re.search(r'(\d+)\s*(?:day|d)', lower_str)
            if day_match:
                days = float(day_match.group(1))
                hours = days * 24.0
                return (hours <= max_hours, round(hours, 1))

            if "today" in lower_str:
                return True, 4.0
            if "yesterday" in lower_str:
                return False, 26.0

            # Parse standard ISO / RFC formats with dateutil
            dt = date_parser.parse(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            age_seconds = (now_utc - dt).total_seconds()
            # If date is slightly in future due to clock skew, clamp to 0
            age_seconds = max(0.0, age_seconds)
            age_hours = age_seconds / 3600.0

            return (age_hours <= max_hours, round(age_hours, 1))
        except Exception as e:
            # Fallback: if unparseable, don't drop blindly if not clearly old
            return True, 0.0
