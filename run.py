import sys
import argparse
import uvicorn
import webbrowser
from config.settings import settings
from database.db import init_db
from scrapers.orchestrator import JobHunterOrchestrator
from email_engine.imap_tracker import IMAPInboxTracker
from email_engine.smtp_digest import EmailDigestSender
from database.db import get_jobs

def print_banner():
    banner = f"""
========================================================================
       🚀 GLOBAL JOB HUNTER AI AUTOMATION SYSTEM ($0 COST)
========================================================================
  • Candidate:     {settings.CANDIDATE_NAME}
  • Target Roles:  {', '.join(settings.target_roles[:3])}
  • Modalities:    Worldwide Remote + US/UK/EU/UAE/AU Relocation
  • AI Brain:      Google Gemini Free Tier / Groq Free API
  • Job Feeds:     RemoteOK, Remotive, WeWorkRemotely, Jobicy
  • Dashboard:     http://{settings.HOST}:{settings.PORT}
========================================================================
"""
    print(banner)

def main():
    parser = argparse.ArgumentParser(description="Global Job Hunter AI Automation System")
    parser.add_argument("--hunt", action="store_true", help="Run one-shot job hunting pipeline directly in CLI")
    parser.add_argument("--check-email", action="store_true", help="Check Gmail IMAP for recruiter replies and interview invites")
    parser.add_argument("--digest", action="store_true", help="Dispatch daily email digest with top matched jobs")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port for the dashboard server")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open dashboard in web browser")

    args = parser.parse_args()

    # Initialize SQLite database
    init_db()
    print_banner()

    if args.hunt:
        print("[CLI Mode] Launching autonomous job hunting cycle...")
        orchestrator = JobHunterOrchestrator()
        result = orchestrator.run_hunt()
        print(f"\n[CLI Mode] Finished: {result}")
        sys.exit(0)

    if args.check_email:
        print("[CLI Mode] Checking Gmail inbox for recruiter communications...")
        tracker = IMAPInboxTracker()
        replies = tracker.check_inbox()
        print(f"[CLI Mode] Found {len(replies)} recruiter replies.")
        sys.exit(0)

    if args.digest:
        print("[CLI Mode] Dispatching daily email digest...")
        top_jobs = get_jobs(min_score=settings.MATCH_THRESHOLD, limit=5)
        success = EmailDigestSender().send_daily_digest(top_jobs)
        print(f"[CLI Mode] Digest sent: {success}")
        sys.exit(0)

    # Launch FastAPI Server
    dashboard_url = f"http://{settings.HOST}:{args.port}"
    print(f"✨ Starting Dark-Mode Dashboard UI at: {dashboard_url}")
    print("Press Ctrl+C to stop the system.\n")

    if not args.no_browser:
        try:
            webbrowser.open(dashboard_url)
        except Exception:
            pass

    uvicorn.run(
        "dashboard.app:app",
        host=settings.HOST,
        port=args.port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
