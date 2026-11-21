import threading
import time
from datetime import datetime
from typing import Optional
from config.settings import settings
from scrapers.orchestrator import JobHunterOrchestrator
from email_engine.imap_tracker import IMAPInboxTracker
from email_engine.smtp_digest import EmailDigestSender
from database.db import get_jobs

class AutonomousScheduler:
    def __init__(self):
        self._hunt_thread: Optional[threading.Thread] = None
        self._imap_thread: Optional[threading.Thread] = None
        self._running = False
        self.last_hunt_time: Optional[str] = None
        self.last_imap_time: Optional[str] = None
        self.auto_pilot_enabled: bool = settings.AUTO_PILOT_ENABLED
        self.continuous_mode: bool = settings.CONTINUOUS_HUNT_MODE
        self.cooldown_seconds: int = settings.CONTINUOUS_COOLDOWN_SECONDS if self.continuous_mode else (settings.AUTO_PILOT_INTERVAL_MINUTES * 60)
        self.interval_minutes: int = max(1, self.cooldown_seconds // 60)
        self.seconds_until_next_hunt: int = self.cooldown_seconds
        self.log_callback = None

    def start(self):
        if self._running:
            return
        self._running = True

        # 1. Start IMAP poller thread (runs every 15 minutes)
        self._imap_thread = threading.Thread(target=self._imap_loop, daemon=True)
        self._imap_thread.start()

        # 2. Start Continuous / Autonomous Hunt & Auto-Apply loop
        self._hunt_thread = threading.Thread(target=self._autonomous_hunt_loop, daemon=True)
        self._hunt_thread.start()

        mode_desc = "Continuous Scanning Mode (Auto-scanning continuously)" if self.continuous_mode else f"every {self.interval_minutes} minutes"
        print(f"[Scheduler] Autonomous Auto-Pilot Active! {mode_desc} for fresh (<24h) jobs.")

    def stop(self):
        self._running = False
        print("[Scheduler] Scheduler stopped.")

    def is_active(self) -> bool:
        return self._running

    def toggle_auto_pilot(self, enabled: bool, interval_mins: Optional[int] = None):
        self.auto_pilot_enabled = enabled
        if interval_mins:
            self.interval_minutes = interval_mins
            self.cooldown_seconds = interval_mins * 60
            self.seconds_until_next_hunt = self.cooldown_seconds
        print(f"[Scheduler] Auto-Pilot toggled: {self.auto_pilot_enabled} (Continuous: {self.continuous_mode}, Interval: {self.interval_minutes}m)")

    def _autonomous_hunt_loop(self):
        # Initial delay before first background cycle so app starts up cleanly
        time.sleep(5)

        # Run first autonomous cycle immediately on startup if enabled
        if self.auto_pilot_enabled:
            try:
                self._execute_cycle()
            except Exception as e:
                print(f"[Scheduler Loop] Initial cycle error: {e}")

        timer = self.cooldown_seconds
        while self._running:
            try:
                time.sleep(1)
                timer -= 1
                self.seconds_until_next_hunt = max(0, timer)

                # Check periodic interval / continuous trigger
                if timer <= 0:
                    if self.auto_pilot_enabled:
                        try:
                            self._execute_cycle()
                        except Exception as e:
                            print(f"[Scheduler Loop] Cycle error: {e}")
                    timer = self.cooldown_seconds

                # Also check daily digest time (e.g. 09:00)
                now = datetime.now()
                if now.strftime("%H:%M") == settings.DAILY_DIGEST_TIME and now.second < 2:
                    if settings.ENABLE_EMAIL_DIGEST:
                        try:
                            top_jobs = get_jobs(min_score=settings.MATCH_THRESHOLD, limit=10)
                            EmailDigestSender().send_daily_digest(top_jobs)
                        except Exception as de:
                            print(f"[Scheduler Loop] Digest error: {de}")
            except Exception as outer_e:
                print(f"[Scheduler Loop] Iteration notice: {outer_e}")
                time.sleep(2)

    def _execute_cycle(self):
        cb = self.log_callback or (lambda msg: print(f"[Scheduler] {msg}"))
        try:
            cb(f"🚀 [Auto-Pilot Background] Autonomous cycle triggered! Scanning fresh (<24h) jobs & auto-applying...")
            hunter = JobHunterOrchestrator(log_callback=cb)
            res = hunter.run_hunt()
            self.last_hunt_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cb(f"✅ [Auto-Pilot Background] Cycle Completed: {res}")
        except Exception as e:
            try:
                cb(f"⚠️ [Auto-Pilot Background] Hunt Notice: {e}")
            except Exception:
                print(f"⚠️ [Auto-Pilot Background] Hunt Notice: {e}")

    def _imap_loop(self):
        while self._running:
            if settings.ENABLE_RECRUITER_TRACKER:
                try:
                    tracker = IMAPInboxTracker()
                    tracker.check_inbox()
                    self.last_imap_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"[Scheduler] IMAP check notice: {e}")
            time.sleep(900)

scheduler = AutonomousScheduler()
