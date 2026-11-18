# 🚀 Autonomous Global Job Hunter & Auto-Applicant AI ($0 Monthly Cost)

An autonomous, 100% FREE, modern, and production-grade Job Hunting & Auto-Apply Automation System that runs entirely on your local PC. It continuously searches genuine, live tech opportunities worldwide (Remote + Visa Sponsored / Relocation), enforces a strict **< 24 Hours Freshness Filter**, evaluates matches against your master CV with AI, generates tailored ATS resumes & cover letters (PDF), **autonomously submits applications**, and tracks recruiter replies in your Gmail inbox.

---

## 🌟 Key Upgraded Features

### 1. Autonomous Job Search & Auto-Pilot Scheduler
- **Zero-Touch Background Hunting:** Scans worldwide job boards automatically on a recurring schedule (default every 60 minutes) without requiring any manual button clicks.
- **Auto-Pilot Toggle:** Easily pause or resume autonomous background hunting from the dashboard header or settings.

### 2. Strict 24-Hour Freshness Filter (< 24 Hours Only)
- **Authentic Fresh Feeds:** Evaluates the exact publication timestamps across all integrated job boards (Arbeitnow, WeWorkRemotely, Remotive, RemoteOK, Jobicy).
- **Hard Freshness Guard:** Automatically filters out any job posted older than 24 hours (`MAX_JOB_AGE_HOURS=24`), guaranteeing that you are always among the very first applicants to every fresh listing.

### 3. Autonomous Auto-Apply Agent (Playwright + Direct Email)
- **Automatic Form Submission:** For jobs matching $\ge 75\%$ suitability, the autonomous applicant:
  1. Auto-detects application forms.
  2. Pre-fills candidate details (Full Name, Email, Phone, LinkedIn, GitHub, Portfolio).
  3. Automatically uploads the newly tailored ATS Resume PDF (`applications/{Company}_{JobTitle}_CV.pdf`).
  4. Fills the tailored Cover Letter.
  5. Clicks the Submit button safely and verifies submission.
  6. **Anti-Bot & CAPTCHA Safety:** If a security challenge or Cloudflare Turnstile/hCaptcha is detected, it pauses safely to protect your account and alerts you on the dashboard.
- **Direct Email Auto-Apply:** For postings with direct `mailto:` or recruiter application emails, automatically sends a formal application email with tailored CV and Cover Letter attached.

### 4. Zero-Cost AI Brain & ATS Generator
- **AI Brain (Free Tier):** Google Gemini Free Tier (`gemini-1.5-flash`) / Groq Free API (`llama-3.3-70b-versatile`) with local heuristic fallback.
- **Tailored ATS Resume & Cover Letter:** Generates customized ATS-compliant resumes and bespoke cover letters as PDFs in `applications/`.
- **24/7 Recruiter Inbox Tracker:** IMAP scanner detects recruiter responses & interview requests in Gmail and highlights them in real time.

---

## 📂 Project Structure

```
job-hunter/
├── .env                          # Configuration (API keys, 24h filter, Auto-Apply toggle)
├── .env.example                  # Template configuration
├── requirements.txt              # All zero-cost python dependencies
├── run.py                        # Single-command launcher (CLI & Web Dashboard)
├── config/
│   ├── settings.py               # Pydantic settings & loader
│   └── my_profile.json           # Your skills, target roles, locations, experience
├── data/
│   ├── master_cv.txt             # Your complete master CV in text format
│   └── job_hunter.db             # Local SQLite database
├── database/
│   ├── db.py                     # SQLite helper queries, deduplication, migrations
│   └── models.py                 # Pydantic schemas
├── scrapers/
│   ├── base_scraper.py           # Base scraper with <24h age filter & role synonyms
│   ├── arbeitnow.py              # Arbeitnow live API (hourly fresh global tech jobs)
│   ├── weworkremotely.py         # WeWorkRemotely RSS feed scraper
│   ├── remotive.py               # Remotive authentic API scraper
│   ├── remoteok.py               # RemoteOK authentic API scraper
│   ├── jobicy.py                 # Jobicy authentic API scraper
│   ├── autonomous_applicant.py   # Autonomous Auto-Apply agent (Playwright + Email)
│   ├── playwright_safe.py        # Safe Playwright browser assistant
│   └── orchestrator.py           # Multi-source pipeline orchestrator
├── ai_engine/
│   ├── gemini_matcher.py         # Gemini AI match scorer (0-100% + 3 bullets + gaps)
│   └── doc_tailor.py             # Generates tailored Cover Letter & ATS summary
├── generators/
│   └── pdf_generator.py          # ReportLab ATS Resume & Cover Letter PDF builder
├── email_engine/
│   ├── smtp_digest.py            # Daily HTML Job Digest email + attachments
│   └── imap_tracker.py           # 24/7 IMAP scanner for recruiter replies
├── scheduler/
│   └── job_scheduler.py          # Background autonomous scheduler (Auto-Pilot)
├── dashboard/
│   ├── app.py                    # FastAPI server with SSE live streaming
│   ├── static/js/app.js          # Reactive dashboard client logic
│   └── templates/index.html      # Modern Dark-Mode TailwindCSS dashboard
└── applications/                 # AI-generated tailored PDFs saved here
```

---

## ⚡ Quickstart Setup Guide

### 1. Start the Autonomous System
```bash
cd c:\Users\User\Downloads\job-hunter
python run.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

- The system starts in **Autonomous Auto-Pilot Mode**:
  - Automatically searches every 60 minutes.
  - Strictly targets jobs posted in the last 24 hours.
  - Automatically matches and applies to high-fit roles.
- You can watch the autonomous bot fill forms and submit applications in the **Live Terminal**.
- Under the **Auto-Applied** filter, see all jobs that have been submitted on your behalf.
- Under **Recruiter Replies**, see inbound interview requests detected by the IMAP tracker.

### 2. Headless CLI Commands
```bash
# Run one-shot search (<24h) and auto-apply cycle from terminal:
python run.py --hunt

# Check Gmail for recruiter replies and alert:
python run.py --check-email

# Dispatch daily email digest:
python run.py --digest
```
