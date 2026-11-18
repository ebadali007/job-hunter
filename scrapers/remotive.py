import requests
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper, USER_AGENTS
from config.settings import settings

class RemotiveScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="remotive")
        self.endpoint = "https://remotive.com/api/remote-jobs"

    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": USER_AGENTS[0]}
        params = {"category": "software-dev", "limit": 40}
        results: List[Dict[str, Any]] = []

        try:
            response = requests.get(self.endpoint, params=params, headers=headers, timeout=12)
            if response.status_code != 200:
                return results

            data = response.json()
            jobs = data.get("jobs", [])

            for item in jobs:
                title = item.get("title", "").strip()
                company = item.get("company_name", "Unknown").strip()
                raw_desc = item.get("description", "")
                clean_desc = self.clean_html(raw_desc)
                location = item.get("candidate_required_location", "Worldwide Remote")
                tags_list = item.get("tags", [])
                tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(tags_list)
                salary = item.get("salary", "") or "Competitive / Disclosed in Interview"

                # Filter by 24h freshness
                pub_date = item.get("publication_date", "")
                is_fresh, age_hours = self.is_posted_under_24h(pub_date, max_hours=settings.MAX_JOB_AGE_HOURS)
                if not is_fresh:
                    continue

                # Filter by role & location
                if not self.is_role_match(title, clean_desc, tags_str, target_roles):
                    continue
                if not self.is_location_match(location, target_locations):
                    continue

                apply_url = item.get("url", "")
                ext_id = str(item.get("id", "")) or apply_url

                results.append({
                    "source": self.name,
                    "external_id": ext_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "is_remote": True,
                    "salary": salary,
                    "apply_url": apply_url,
                    "description": clean_desc,
                    "tags": tags_str,
                    "posted_at": pub_date,
                    "age_hours": age_hours
                })
        except Exception as e:
            print(f"[RemotiveScraper] Error fetching jobs: {e}")

        return results
