import time
import os
from typing import Dict, Any, Optional
from pathlib import Path
from config.settings import settings

class PlaywrightSafeAssistant:
    """
    Assists in safe form pre-filling for simple job application pages.
    Detects anti-bot/CAPTCHA and pauses immediately to safeguard candidate accounts.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless

    def autofill_application(
        self,
        job_url: str,
        tailored_cv_path: Optional[str] = None,
        cover_letter_text: Optional[str] = None
    ) -> Dict[str, Any]:
        from playwright.sync_api import sync_playwright

        profile = settings.get_profile()
        contact = profile.get("contact", {})
        full_name = profile.get("name", settings.CANDIDATE_NAME)
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)
        github = contact.get("github", settings.CANDIDATE_GITHUB)
        portfolio = contact.get("portfolio", settings.CANDIDATE_PORTFOLIO)

        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        report = {
            "status": "pending",
            "captcha_detected": False,
            "fields_filled": [],
            "resume_attached": False,
            "message": ""
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled"
                    ]
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                # Navigate to the job apply page
                page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(2)

                # Check for CAPTCHA / Cloudflare / bot challenges
                page_content = page.content().lower()
                captcha_signatures = [
                    "cf-challenge", "cf-turnstile", "hcaptcha", "recaptcha",
                    "g-recaptcha", "verify you are human", "security check",
                    "bot detection", "perimeterx", "datadome"
                ]

                for sig in captcha_signatures:
                    if sig in page_content:
                        report["captcha_detected"] = True
                        report["status"] = "captcha_paused"
                        report["message"] = (
                            f"Anti-Bot / CAPTCHA detected ({sig}). "
                            "Automated submission halted to protect candidate profile. "
                            "Please complete in browser manually."
                        )
                        browser.close()
                        return report

                # Safe Pre-Fill Detection
                # 1. Name fields
                self._safe_fill(page, ['input[name*="name" i]', 'input[id*="name" i]', 'input[placeholder*="full name" i]'], full_name, "Full Name", report)
                self._safe_fill(page, ['input[name*="first" i]', 'input[id*="first" i]'], first_name, "First Name", report)
                self._safe_fill(page, ['input[name*="last" i]', 'input[id*="last" i]'], last_name, "Last Name", report)

                # 2. Email field
                self._safe_fill(page, ['input[type="email"]', 'input[name*="email" i]', 'input[id*="email" i]'], email, "Email", report)

                # 3. Phone field
                self._safe_fill(page, ['input[type="tel"]', 'input[name*="phone" i]', 'input[id*="phone" i]'], phone, "Phone", report)

                # 4. Social links (LinkedIn, GitHub, Portfolio)
                self._safe_fill(page, ['input[name*="linkedin" i]', 'input[id*="linkedin" i]', 'input[placeholder*="linkedin" i]'], linkedin, "LinkedIn", report)
                self._safe_fill(page, ['input[name*="github" i]', 'input[id*="github" i]'], github, "GitHub", report)
                self._safe_fill(page, ['input[name*="portfolio" i]', 'input[name*="website" i]'], portfolio, "Portfolio", report)

                # 5. Cover letter text area
                if cover_letter_text:
                    self._safe_fill(page, ['textarea[name*="cover" i]', 'textarea[id*="cover" i]', 'textarea[placeholder*="cover letter" i]'], cover_letter_text[:1200], "Cover Letter", report)

                # 6. File upload (CV / Resume PDF)
                if tailored_cv_path and os.path.exists(tailored_cv_path):
                    file_input = page.query_selector('input[type="file"]')
                    if file_input:
                        try:
                            file_input.set_input_files(str(Path(tailored_cv_path).resolve()))
                            report["resume_attached"] = True
                            report["fields_filled"].append("Tailored CV File Attached")
                        except Exception as ex:
                            print(f"[PlaywrightAssistant] File attach warning: {ex}")

                report["status"] = "prefilled_ready"
                report["message"] = (
                    f"Successfully pre-filled {len(report['fields_filled'])} form fields. "
                    "Final submit left for candidate confirmation."
                )
                time.sleep(2)
                browser.close()

        except Exception as e:
            report["status"] = "error"
            report["message"] = f"Playwright automation encountered notice: {str(e)}"

        return report

    def _safe_fill(self, page, selectors: list, value: str, field_name: str, report: dict):
        if not value:
            return
        for sel in selectors:
            try:
                elem = page.query_selector(sel)
                if elem and elem.is_visible() and elem.is_enabled():
                    current_val = elem.input_value() if hasattr(elem, "input_value") else ""
                    if not current_val:
                        elem.fill(value)
                        report["fields_filled"].append(field_name)
                        break
            except Exception:
                continue
