import time
import json
import traceback
from typing import List, Dict, Any, Callable, Optional
from config.settings import settings
from database.db import save_job, update_job_match, log_hunting_run, mark_job_status
from scrapers.remotive import RemotiveScraper
from scrapers.remoteok import RemoteOKScraper
from scrapers.weworkremotely import WeWorkRemotelyScraper
from scrapers.jobicy import JobicyScraper
from scrapers.arbeitnow import ArbeitnowScraper
from scrapers.autonomous_applicant import AutonomousApplicant
from ai_engine.gemini_matcher import GeminiJobMatcher
from ai_engine.doc_tailor import DocumentTailor
from generators.pdf_generator import PDFGenerator
from email_engine.smtp_digest import EmailDigestSender

class JobHunterOrchestrator:
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.log_callback = log_callback or (lambda msg: print(f"[Hunter] {msg}"))
        self.scrapers = [
            ArbeitnowScraper(),
            WeWorkRemotelyScraper(),
            RemotiveScraper(),
            RemoteOKScraper(),
            JobicyScraper()
        ]
        self.matcher = GeminiJobMatcher()
        self.tailor = DocumentTailor()
        self.pdf_gen = PDFGenerator()
        self.applicant = AutonomousApplicant(log_callback=self.log, headless=True)

    def log(self, message: str):
        self.log_callback(message)

    def run_hunt(self) -> Dict[str, Any]:
        """
        Autonomous pipeline:
        Scraping (< 24h) -> Deduplication -> AI Scoring -> ATS Document Tailoring -> Autonomous Auto-Apply -> Persistence.
        """
        start_time = time.time()
        self.log("🚀 Initializing Global Autonomous Job Hunter Pipeline...")
        self.log(f"🕒 [Freshness Filter] Enforcing < {settings.MAX_JOB_AGE_HOURS} hours post age (Fresh Jobs Only)")
        self.log(f"🤖 [Auto-Apply] Status: {'ENABLED (Automatic Application)' if settings.AUTO_APPLY_ENABLED else 'MANUAL (One-Click)'}")

        target_roles = settings.target_roles
        target_locations = settings.target_locations
        master_cv = settings.get_master_cv()

        self.log(f"📋 Target Roles: {', '.join(target_roles[:4])}")
        self.log(f"🌍 Target Locations: {', '.join(target_locations[:4])}")
        self.log(f"🎯 Match Threshold: {settings.MATCH_THRESHOLD}%")

        all_scraped: List[Dict[str, Any]] = []
        sources_list = []

        # 1. Multi-source scraping (filtered by < 24h)
        for scraper in self.scrapers:
            try:
                self.log(f"🔎 Scanning fresh (<24h) opportunities from {scraper.name.upper()}...")
                jobs = scraper.fetch_jobs(target_roles, target_locations)
                self.log(f"✅ [{scraper.name.upper()}] Found {len(jobs)} fresh jobs matching criteria.")
                all_scraped.extend(jobs)
                sources_list.append(scraper.name)
            except Exception as e:
                self.log(f"⚠️ Warning scraping {scraper.name}: {e}")

        self.log(f"📦 Total raw fresh opportunities collected: {len(all_scraped)}")

        # 2. Database deduplication, AI Scoring, Tailoring, and Autonomous Auto-Apply
        new_jobs_count = 0
        high_matches_count = 0
        auto_applied_count = 0
        high_match_jobs_list: List[Dict[str, Any]] = []

        for idx, job in enumerate(all_scraped, start=1):
            try:
                job_id, is_new = save_job(job)
                if not is_new:
                    continue

                new_jobs_count += 1
                job["id"] = job_id

                age_info = f" (Posted {job.get('age_hours', 0)}h ago)" if "age_hours" in job else ""
                self.log(f"⚡ [{new_jobs_count}] Evaluating with AI Brain: {job['title']} @ {job['company']}{age_info}")

                # 3. AI Skill Matching & Scoring Agent
                match_result = self.matcher.match_job(
                    job_title=job["title"],
                    company=job["company"],
                    job_description=job["description"],
                    cv_text=master_cv
                )

                score = match_result.get("match_score", 0)
                reasons = match_result.get("match_reasons", [])
                gaps = match_result.get("skill_gaps", [])

                cv_path = None
                cl_path = None
                cl_text = None
                res_summary = None
                is_applied = False

                # 4. Tailoring for High Matches (>= MATCH_THRESHOLD)
                if score >= settings.MATCH_THRESHOLD:
                    high_matches_count += 1
                    self.log(f"🌟 HIGH MATCH ({score}%): {job['title']} @ {job['company']}! Tailoring ATS Package...")

                    tailored_docs = self.tailor.tailor_documents(
                        job_title=job["title"],
                        company=job["company"],
                        job_description=job["description"],
                        cv_text=master_cv
                    )

                    cl_text = tailored_docs.get("cover_letter")
                    res_summary = tailored_docs.get("resume_summary")

                    cv_path, cl_path = self.pdf_gen.generate_tailored_pdf_package(
                        company=job["company"],
                        job_title=job["title"],
                        tailored_data=tailored_docs
                    )

                    job["tailored_cv_path"] = cv_path
                    job["tailored_cl_path"] = cl_path
                    job["tailored_cover_letter_text"] = cl_text
                    job["tailored_resume_summary"] = res_summary
                    job["match_score"] = score
                    job["match_reasons"] = json.dumps(reasons)
                    high_match_jobs_list.append(job)

                    self.log(f"📄 Tailored ATS Resume & Cover Letter PDF ready for {job['company']}.")

                    # 5. AUTONOMOUS AUTO-APPLY
                    if settings.AUTO_APPLY_ENABLED and score >= settings.AUTO_APPLY_MIN_SCORE:
                        self.log(f"🚀 [Auto-Apply Trigger] Automatically submitting application for {job['company']}...")
                        apply_res = self.applicant.apply_job(job)
                        if apply_res.get("status") == "applied":
                            auto_applied_count += 1
                            is_applied = True
                            mark_job_status(job_id, "applied")

                # Update job in database
                update_job_match(
                    job_id=job_id,
                    score=score,
                    reasons=reasons,
                    gaps=gaps,
                    tailored_cv_path=cv_path,
                    tailored_cl_path=cl_path,
                    cover_letter_text=cl_text,
                    resume_summary=res_summary,
                    status="applied" if is_applied else None
                )

            except Exception as item_err:
                self.log(f"⚠️ Error processing job {job.get('title')}: {item_err}")

        # 6. Optional Email Digest dispatch
        if settings.ENABLE_EMAIL_DIGEST and high_match_jobs_list:
            self.log(f"📧 Sending Daily Email Digest with {len(high_match_jobs_list)} high-match jobs...")
            EmailDigestSender().send_daily_digest(high_match_jobs_list)

        duration = round(time.time() - start_time, 2)
        summary_log = (
            f"🎉 Autonomous Cycle Finished in {duration}s! Fresh (<24h): {len(all_scraped)} | "
            f"New: {new_jobs_count} | High Matches: {high_matches_count} | Auto-Applied: {auto_applied_count}"
        )
        self.log(summary_log)

        log_hunting_run(
            sources=", ".join(sources_list),
            found=len(all_scraped),
            new_jobs=new_jobs_count,
            high_matches=high_matches_count,
            status="completed",
            logs=summary_log
        )

        return {
            "scraped": len(all_scraped),
            "new": new_jobs_count,
            "high_matches": high_matches_count,
            "auto_applied": auto_applied_count,
            "duration": duration
        }
