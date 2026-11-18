import requests
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper, USER_AGENTS
from config.settings import settings

class RemoteOKScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="remoteok")
        self.endpoint = "https://remoteok.com/api"

    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": USER_AGENTS[0], "Accept": "application/json"}
        results: List[Dict[str, Any]] = []

        try:
            response = requests.get(self.endpoint, headers=headers, timeout=12)
            if response.status_code != 200:
                return results

            data = response.json()
            # RemoteOK first entry is disclaimer
            job_items = [j for j in data if isinstance(j, dict) and "position" in j]

            for item in job_items:
                title = item.get("position", "").strip()
                company = item.get("company", "Unknown").strip()
                raw_desc = item.get("description", "")
                clean_desc = self.clean_html(raw_desc)
                location = item.get("location", "") or "Worldwide Remote"
                tags_list = item.get("tags", [])
                tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(tags_list)

                # Format salary if available
                min_sal = item.get("salary_min")
                max_sal = item.get("salary_max")
                if min_sal and max_sal:
                    salary = f"${min_sal:,} - ${max_sal:,} USD"
                elif min_sal:
                    salary = f"${min_sal:,}+ USD"
                else:
                    salary = "Competitive / Disclosed in Interview"

                # Filter by 24h freshness
                date_val = item.get("epoch") or item.get("date", "")
                is_fresh, age_hours = self.is_posted_under_24h(date_val, max_hours=settings.MAX_JOB_AGE_HOURS)
                if not is_fresh:
                    continue

                # Filter by role & location
                if not self.is_role_match(title, clean_desc, tags_str, target_roles):
                    continue
                if not self.is_location_match(location, target_locations):
                    continue

                url = item.get("url", "")
                if url and not url.startswith("http"):
                    apply_url = f"https://remoteok.com{url}"
                else:
                    apply_url = url or item.get("apply_url", "")

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
                    "posted_at": str(item.get("date", "")),
                    "age_hours": age_hours
                })
        except Exception as e:
            print(f"[RemoteOKScraper] Error fetching jobs: {e}")

        return results
