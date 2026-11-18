import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from scrapers.base_scraper import BaseScraper, USER_AGENTS
from config.settings import settings

class WeWorkRemotelyScraper(BaseScraper):
    FEEDS = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"
    ]

    def __init__(self):
        super().__init__(name="weworkremotely")

    def fetch_jobs(self, target_roles: List[str], target_locations: List[str]) -> List[Dict[str, Any]]:
        headers = {"User-Agent": USER_AGENTS[0]}
        results: List[Dict[str, Any]] = []
        seen_urls = set()

        for feed_url in self.FEEDS:
            try:
                response = requests.get(feed_url, headers=headers, timeout=12)
                if response.status_code != 200:
                    continue

                root = ET.fromstring(response.content)
                items = root.findall(".//item")

                for item in items:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    pub_elem = item.find("pubDate")
                    guid_elem = item.find("guid")

                    raw_title = title_elem.text if title_elem is not None else ""
                    apply_url = link_elem.text if link_elem is not None else ""
                    raw_desc = desc_elem.text if desc_elem is not None else ""
                    pub_date = pub_elem.text if pub_elem is not None else ""
                    ext_id = guid_elem.text if guid_elem is not None else apply_url

                    if not apply_url or apply_url in seen_urls:
                        continue
                    seen_urls.add(apply_url)

                    # WWR title format is typically "Company Name: Job Title"
                    company = "Unknown"
                    title = raw_title
                    if ":" in raw_title:
                        parts = raw_title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    clean_desc = self.clean_html(raw_desc)
                    location = "Worldwide Remote"

                    # Filter by 24h freshness
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
                        "salary": "Competitive / Disclosed in JD",
                        "apply_url": apply_url,
                        "description": clean_desc,
                        "tags": "full-stack, frontend, remote",
                        "posted_at": pub_date,
                        "age_hours": age_hours
                    })
            except Exception as e:
                print(f"[WeWorkRemotelyScraper] Feed error on {feed_url}: {e}")

        return results
