import requests
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper, USER_AGENTS
from config.settings import settings

class ArbeitnowScraper(BaseScraper):
    """
    Arbeitnow authentic free public job board API.
    Provides fresh European, Visa-Sponsored, and Worldwide Remote tech jobs updated hourly.
    """
    def __init__(self):
        super().__init__(name="arbeitnow")
        self.endpoint = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": USER_AGENTS[0], "Accept": "application/json"}
        results: List[Dict[str, Any]] = []

        try:
            response = requests.get(self.endpoint, headers=headers, timeout=14)
            if response.status_code != 200:
                return results

            data = response.json()
            items = data.get("data", [])

            for item in items:
                title = item.get("title", "").strip()
                company = item.get("company_name", "Unknown").strip()
                raw_desc = item.get("description", "")
                clean_desc = self.clean_html(raw_desc)
                location = item.get("location", "") or "Worldwide Remote"
                is_remote = item.get("remote", True)
                tags_list = item.get("tags", [])
                tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(tags_list)
                created_epoch = item.get("created_at")

                # Strictly filter by 24h freshness (< 24 hours)
                is_fresh, age_hours = self.is_posted_under_24h(created_epoch, max_hours=settings.MAX_JOB_AGE_HOURS)
                if not is_fresh:
                    continue

                # Filter by role & location
                if not self.is_role_match(title, clean_desc, tags_str, target_roles):
                    continue
                if not self.is_location_match(location, target_locations):
                    continue

                apply_url = item.get("url", "")
                ext_id = item.get("slug") or str(created_epoch) or apply_url

                results.append({
                    "source": self.name,
                    "external_id": ext_id,
                    "title": title,
                    "company": company,
                    "location": f"{location} (Remote)" if is_remote and "remote" not in location.lower() else location,
                    "is_remote": is_remote,
                    "salary": "Competitive / Disclosed in JD",
                    "apply_url": apply_url,
                    "description": clean_desc,
                    "tags": tags_str,
                    "posted_at": str(created_epoch),
                    "age_hours": age_hours
                })
        except Exception as e:
            print(f"[ArbeitnowScraper] Error fetching jobs: {e}")

        return results
