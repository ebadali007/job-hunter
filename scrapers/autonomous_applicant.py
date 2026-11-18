import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from config.settings import settings
from database.db import mark_job_status
from email_engine.smtp_digest import EmailDigestSender

class AutonomousApplicant:
    """
    Autonomous Job Application Agent with Deep ATS Support (Greenhouse, Lever, Workable, Direct Forms).
    Follows job aggregator redirects, populates candidate profile, attaches tailored ATS Resume,
    handles standard compliance questions, and submits applications safely.
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None, headless: bool = True):
        self.log = log_callback or (lambda msg: print(f"[AutoApplicant] {msg}"))
        self.headless = headless

    def apply_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main autonomous application entrypoint for a high-match fresh job.
        """
        title = job.get("title", "")
        company = job.get("company", "")
        apply_url = job.get("apply_url", "")
        cv_path = job.get("tailored_cv_path")
        cl_text = job.get("tailored_cover_letter_text")

        self.log(f"🤖 [Auto-Apply] Initiating autonomous application for: {title} @ {company}...")

        # 1. Check for Direct Email Apply (mailto: or email in JD)
        email_target = self._extract_apply_email(apply_url, job.get("description", ""))
        if email_target:
            return self._apply_via_email(job, email_target, cv_path, cl_text)

        # 2. Apply via Playwright Web Form Assistant
        return self._apply_via_web_form(job, cv_path, cl_text)

    def _extract_apply_email(self, apply_url: str, description: str) -> Optional[str]:
        if apply_url.startswith("mailto:"):
            return apply_url.replace("mailto:", "").split("?")[0].strip()

        match = re.search(r'(?:apply|send resume|submit application|email)\s*(?:to|at)?\s*[:\s]+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', description, re.IGNORECASE)
        if match:
            found_email = match.group(1).strip()
            if not any(bad in found_email.lower() for bad in ["noreply", "support", "help", "privacy"]):
                return found_email
        return None

    def _apply_via_email(self, job: Dict[str, Any], recipient_email: str, cv_path: Optional[str], cl_text: Optional[str]) -> Dict[str, Any]:
        title = job.get("title", "")
        company = job.get("company", "")
        job_id = job.get("id")

        self.log(f"✉️ [Auto-Apply Email] Discovered direct application email: {recipient_email}")

        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)

        subject = f"Application for {title} - {name}"
        body = cl_text or f"Dear Hiring Team at {company},\n\nPlease find attached my resume for the {title} position.\n\nSincerely,\n{name}"

        sender = EmailDigestSender()
        if sender.is_configured():
            try:
                import smtplib
                from email.mime.multipart import MIMEMultipart
                from email.mime.text import MIMEText
                from email.mime.application import MIMEApplication

                msg = MIMEMultipart()
                msg["Subject"] = subject
                msg["From"] = f"{name} <{settings.GMAIL_USER}>"
                msg["To"] = recipient_email
                msg.attach(MIMEText(body, "plain"))

                if cv_path and os.path.exists(cv_path):
                    with open(cv_path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(cv_path))
                        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(cv_path)}"'
                        msg.attach(part)

                with smtplib.SMTP(sender.smtp_server, sender.smtp_port) as s:
                    s.starttls()
                    s.login(sender.username, sender.password)
                    s.send_message(msg)

                self.log(f"✅ [Auto-Apply Email] Successfully emailed direct application to {recipient_email}!")
                if job_id:
                    mark_job_status(job_id, "applied")
                return {"status": "applied", "channel": "email", "recipient": recipient_email}
            except Exception as e:
                self.log(f"⚠️ [Auto-Apply Email] Notice emailing {recipient_email}: {e}")

        self.log(f"ℹ️ [Auto-Apply Email] Ready to email: {recipient_email}. (Add Gmail app password in Settings to auto-dispatch)")
        return {"status": "email_prepared", "recipient": recipient_email}

    def _apply_via_web_form(self, job: Dict[str, Any], cv_path: Optional[str], cl_text: Optional[str]) -> Dict[str, Any]:
        apply_url = job.get("apply_url", "")
        job_id = job.get("id")
        company = job.get("company", "")
        title = job.get("title", "")

        from playwright.sync_api import sync_playwright

        profile = settings.get_profile()
        contact = profile.get("contact", {})
        full_name = profile.get("name", settings.CANDIDATE_NAME)
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)
        github = contact.get("github", settings.CANDIDATE_GITHUB)
        portfolio = contact.get("portfolio", settings.CANDIDATE_PORTFOLIO)

        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

        self.log(f"🌐 [Auto-Apply Web] Launching Playwright browser worker on {apply_url[:60]}...")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 850},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                # Step 1: Navigate to landing page
                page.goto(apply_url, wait_until="domcontentloaded", timeout=25000)
                time.sleep(2)

                # Step 2: Check for external ATS redirects (Greenhouse, Lever, Workable, Ashby, etc.)
                ats_selectors = [
                    'a[href*="greenhouse.io"]',
                    'a[href*="jobs.lever.co"]',
                    'a[href*="workable.com"]',
                    'a[href*="ashbyhq.com"]',
                    'a[href*="/apply"]',
                    'a:has-text("Apply for this job")',
                    'a:has-text("Apply Now")'
                ]
                for ats_sel in ats_selectors:
                    try:
                        ats_link = page.query_selector(ats_sel)
                        if ats_link and ats_link.is_visible():
                            target_href = ats_link.get_attribute("href")
                            if target_href and target_href.startswith("http") and not target_href.startswith(apply_url):
                                self.log(f"🔗 [ATS Redirect] Following external company portal link: {target_href[:65]}...")
                                page.goto(target_href, wait_until="domcontentloaded", timeout=20000)
                                time.sleep(2)
                                break
                    except Exception:
                        continue

                # Step 3: Anti-Bot / CAPTCHA Check
                page_html = page.content().lower()
                captcha_sigs = ["cf-turnstile", "hcaptcha", "recaptcha", "g-recaptcha", "verify you are human", "security check", "datadome"]
                for sig in captcha_sigs:
                    if sig in page_html:
                        self.log(f"⚠️ [Anti-Bot Safe Pause] Security challenge ({sig}) detected on {company} page. Paused safely to protect your candidate account.")
                        browser.close()
                        return {"status": "captcha_paused", "message": f"CAPTCHA detected ({sig})"}

                # Step 4: Populate Candidate Profile Fields
                filled = []
                # First Name / Last Name / Full Name
                self._fill(page, ['#first_name', 'input[name="first_name"]', 'input[id*="first_name" i]', 'input[autocomplete="given-name"]'], first_name, "First Name", filled)
                self._fill(page, ['#last_name', 'input[name="last_name"]', 'input[id*="last_name" i]', 'input[autocomplete="family-name"]'], last_name, "Last Name", filled)
                self._fill(page, ['input[name="name"]', 'input[id="name"]', 'input[placeholder*="full name" i]'], full_name, "Full Name", filled)

                # Email & Phone
                self._fill(page, ['#email', 'input[type="email"]', 'input[name="email"]', 'input[id*="email" i]'], email, "Email", filled)
                self._fill(page, ['#phone', 'input[type="tel"]', 'input[name="phone"]', 'input[id*="phone" i]'], phone, "Phone", filled)

                # Location & Country
                self._fill(page, ['#candidate-location', 'input[name*="location" i]', 'input[placeholder*="city" i]'], location, "Location", filled)

                # Social / Portfolio
                self._fill(page, ['input[name*="linkedin" i]', 'input[id*="linkedin" i]', 'input[placeholder*="linkedin" i]'], linkedin, "LinkedIn", filled)
                self._fill(page, ['input[name*="github" i]', 'input[id*="github" i]'], github, "GitHub", filled)
                self._fill(page, ['input[name*="website" i]', 'input[name*="portfolio" i]', 'input[id*="website" i]'], portfolio, "Portfolio", filled)

                # Cover Letter
                if cl_text:
                    self._fill(page, ['#cover_letter', 'textarea[name*="cover" i]', 'textarea[id*="cover" i]', 'textarea[name="comments"]'], cl_text[:1500], "Cover Letter", filled)

                # Step 5: Attach Tailored ATS Resume PDF
                if cv_path and os.path.exists(cv_path):
                    file_selectors = [
                        'input[type="file"]#resume',
                        'input[type="file"][name*="resume" i]',
                        'input[type="file"]#attach-resume',
                        'input[type="file"]'
                    ]
                    for f_sel in file_selectors:
                        try:
                            f_input = page.query_selector(f_sel)
                            if f_input:
                                f_input.set_input_files(str(Path(cv_path).resolve()))
                                filled.append("Tailored ATS Resume Attached")
                                self.log(f"📎 [ATS Resume Attached] {os.path.basename(cv_path)}")
                                break
                        except Exception as e:
                            self.log(f"Notice attaching resume: {e}")

                # Step 6: Smart Answers for Compliance & Legal Questions
                self._handle_compliance_questions(page, filled)

                self.log(f"📝 [Auto-Apply Web] Form populated with {len(filled)} candidate data fields.")

                # Step 7: Safe Submission Attempt
                submit_selectors = [
                    '#submit_app',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit application")',
                    'button:has-text("Submit Application")',
                    'button:has-text("Apply Now")',
                    'button:has-text("Send Application")'
                ]

                submitted = False
                for sel in submit_selectors:
                    try:
                        btn = page.query_selector(sel)
                        if btn and btn.is_visible() and btn.is_enabled():
                            btn_text = btn.inner_text().strip()
                            if any(w in btn_text.lower() for w in ["cancel", "search", "back", "login", "sign in"]):
                                continue

                            self.log(f"🚀 [Auto-Apply Web] Submitting application to {company} ('{btn_text}')...")
                            btn.click()
                            time.sleep(3.5)
                            submitted = True
                            break
                    except Exception:
                        continue

                browser.close()

                if submitted:
                    self.log(f"🎉 [Auto-Apply Success] Application for {title} @ {company} submitted autonomously!")
                    if job_id:
                        mark_job_status(job_id, "applied")
                    return {"status": "applied", "channel": "web_form", "fields_filled": filled}
                else:
                    self.log(f"✅ [Auto-Apply Web] Pre-filled application for {company}. Ready in queue for 1-click submit.")
                    return {"status": "prefilled_ready", "channel": "web_form", "fields_filled": filled}

        except Exception as e:
            self.log(f"⚠️ [Auto-Apply Notice] {e}")
            return {"status": "error", "message": str(e)}

    def _fill(self, page, selectors: list, value: str, label: str, filled_list: list):
        if not value:
            return
        for s in selectors:
            try:
                el = page.query_selector(s)
                if el and el.is_visible() and el.is_enabled():
                    curr = el.input_value() if hasattr(el, "input_value") else ""
                    if not curr:
                        el.fill(value)
                        filled_list.append(label)
                        break
            except Exception:
                continue

    def _handle_compliance_questions(self, page, filled_list: list):
        """Intelligently checks and answers standard work auth / sponsorship questions."""
        try:
            # Authorized to work questions -> Select Yes
            page.evaluate("""() => {
                const radios = document.querySelectorAll('input[type="radio"]');
                radios.forEach(r => {
                    const label = r.closest('label')?.innerText?.toLowerCase() || '';
                    if (label.includes('authorized to work') || label.includes('legally authorized')) {
                        if (label.includes('yes')) r.click();
                    }
                });
            }""")

            # GDPR / Consent checkboxes -> Check them
            page.evaluate("""() => {
                const checkboxes = document.querySelectorAll('input[type="checkbox"]');
                checkboxes.forEach(c => {
                    const text = c.closest('label')?.innerText?.toLowerCase() || '';
                    if (text.includes('agree') || text.includes('consent') || text.includes('privacy') || text.includes('policy')) {
                        if (!c.checked) c.click();
                    }
                });
            }""")
        except Exception:
            pass
