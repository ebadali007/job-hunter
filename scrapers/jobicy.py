import requests
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper, USER_AGENTS
from config.settings import settings

class JobicyScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="jobicy")
        self.endpoint = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": USER_AGENTS[0], "Accept": "application/json"}
        params = {"count": 30, "tag": "dev"}
        results: List[Dict[str, Any]] = []

        try:
            response = requests.get(self.endpoint, params=params, headers=headers, timeout=12)
            if response.status_code != 200:
                return results

            data = response.json()
            jobs = data.get("jobs", [])

            for item in jobs:
                title = item.get("jobTitle", "").strip()
                company = item.get("companyName", "Unknown").strip()
                raw_desc = item.get("jobDescription", "")
                clean_desc = self.clean_html(raw_desc)
                location = item.get("jobGeo", "") or "Worldwide Remote"
                apply_url = item.get("url", "")
                ext_id = str(item.get("id", "")) or apply_url

                min_sal = item.get("annualSalaryMin")
                max_sal = item.get("annualSalaryMax")
                cur = item.get("salaryCurrency", "USD")
                if min_sal and max_sal:
                    salary = f"{cur} {min_sal:,} - {max_sal:,}"
                elif min_sal:
                    salary = f"{cur} {min_sal:,}+"
                else:
                    salary = "Competitive / Disclosed in JD"

                # Filter by 24h freshness
                pub_date = item.get("pubDate", "")
                is_fresh, age_hours = self.is_posted_under_24h(pub_date, max_hours=settings.MAX_JOB_AGE_HOURS)
                if not is_fresh:
                    continue

                if not self.is_role_match(title, clean_desc, "", target_roles):
                    continue
                if not self.is_location_match(location, target_locations):
                    continue

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
                    "tags": "software-engineering, remote",
                    "posted_at": pub_date,
                    "age_hours": age_hours
                })
        except Exception as e:
            print(f"[JobicyScraper] Error fetching jobs: {e}")

        return results
