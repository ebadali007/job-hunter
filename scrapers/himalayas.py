import requests
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper, USER_AGENTS
from config.settings import settings

class HimalayasScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="himalayas")
        self.endpoint = "https://himalayas.app/jobs/api"

    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": USER_AGENTS[0], "Accept": "application/json"}
        results: List[Dict[str, Any]] = []

        try:
            response = requests.get(f"{self.endpoint}?limit=60", headers=headers, timeout=12)
            if response.status_code != 200:
                return results

            data = response.json()
            jobs = data.get("jobs", [])

            for item in jobs:
                title = item.get("title", "").strip()
                company = item.get("companyName", "Unknown").strip()
                raw_desc = item.get("description", "")
                clean_desc = self.clean_html(raw_desc)

                loc_restrictions = item.get("locationRestrictions", [])
                location = ", ".join(loc_restrictions) if loc_restrictions else "Worldwide Remote"

                apply_url = item.get("applicationLink") or f"https://himalayas.app/companies/{item.get('companySlug')}/jobs/{item.get('guid')}"
                ext_id = str(item.get("guid") or apply_url)

                min_sal = item.get("minSalary")
                max_sal = item.get("maxSalary")
                cur = item.get("currency", "USD")
                if min_sal and max_sal:
                    salary = f"{cur} {min_sal:,} - {max_sal:,}"
                elif min_sal:
                    salary = f"{cur} {min_sal:,}+"
                else:
                    salary = "Competitive / Disclosed in JD"

                pub_epoch = item.get("pubDate")
                is_fresh, age_hours = self.is_posted_under_24h(pub_epoch, max_hours=settings.MAX_JOB_AGE_HOURS)
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
                    "tags": ", ".join(item.get("categories", [])) or "software-engineering, remote",
                    "posted_at": str(pub_epoch),
                    "age_hours": age_hours
                })
        except Exception as e:
            print(f"[HimalayasScraper] Error: {e}")

        return results
