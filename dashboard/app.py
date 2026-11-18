import os
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, BackgroundTasks, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from database.db import (
    init_db, get_jobs, get_job_by_id, mark_job_status,
    get_recruiter_replies, mark_reply_read, get_dashboard_stats
)
from scrapers.orchestrator import JobHunterOrchestrator
from scrapers.playwright_safe import PlaywrightSafeAssistant
from email_engine.imap_tracker import IMAPInboxTracker
from email_engine.smtp_digest import EmailDigestSender
from scheduler.job_scheduler import scheduler

# Initialize DB
init_db()

app = FastAPI(title="Global Job Hunter AI Automation", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
STATIC_DIR = settings.BASE_DIR / "dashboard" / "static"
TEMPLATES_DIR = settings.BASE_DIR / "dashboard" / "templates"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Shared log queue for Server-Sent Events (SSE)
log_subscribers = []
is_hunting_active = False
main_event_loop = None

def broadcast_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = json.dumps({"message": msg, "time": timestamp})
    print(f"[Live] {msg}", flush=True)
    for queue in list(log_subscribers):
        try:
            if main_event_loop and main_event_loop.is_running():
                main_event_loop.call_soon_threadsafe(queue.put_nowait, formatted)
            else:
                queue.put_nowait(formatted)
        except Exception:
            pass

@app.on_event("startup")
async def startup_event():
    global main_event_loop
    try:
        main_event_loop = asyncio.get_running_loop()
    except Exception:
        main_event_loop = None
    scheduler.log_callback = broadcast_log
    scheduler.start()

# --- WEB UI ROUTE ---
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Dashboard template loading...</h1>")

# --- REST APIS ---
@app.get("/api/stats")
async def api_stats():
    stats = get_dashboard_stats()
    stats["is_hunting"] = is_hunting_active
    stats["scheduler_active"] = scheduler.is_active()
    stats["auto_pilot_enabled"] = scheduler.auto_pilot_enabled
    stats["auto_pilot_interval"] = scheduler.interval_minutes
    stats["seconds_until_next_hunt"] = scheduler.seconds_until_next_hunt
    stats["auto_apply_enabled"] = settings.AUTO_APPLY_ENABLED
    stats["max_job_age_hours"] = settings.MAX_JOB_AGE_HOURS
    return stats

class AutoPilotToggle(BaseModel):
    enabled: bool
    interval_minutes: Optional[int] = None

@app.post("/api/autopilot/toggle")
async def api_toggle_autopilot(payload: AutoPilotToggle):
    scheduler.toggle_auto_pilot(payload.enabled, payload.interval_minutes)
    settings.AUTO_PILOT_ENABLED = payload.enabled
    if payload.interval_minutes:
        settings.AUTO_PILOT_INTERVAL_MINUTES = payload.interval_minutes
    return {
        "success": True,
        "auto_pilot_enabled": scheduler.auto_pilot_enabled,
        "interval_minutes": scheduler.interval_minutes
    }

@app.get("/api/jobs")
async def api_get_jobs(
    status: Optional[str] = "all",
    min_score: int = Query(0, ge=0, le=100),
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    jobs = get_jobs(status=status, min_score=min_score, search=search, limit=limit, offset=offset)
    # Parse json fields for clean client rendering
    for j in jobs:
        if j.get("match_reasons"):
            try:
                j["match_reasons"] = json.loads(j["match_reasons"])
            except Exception:
                j["match_reasons"] = [j["match_reasons"]]
        if j.get("skill_gaps"):
            try:
                j["skill_gaps"] = json.loads(j["skill_gaps"])
            except Exception:
                j["skill_gaps"] = [j["skill_gaps"]]
    return jobs

@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: int):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("match_reasons"):
        try:
            job["match_reasons"] = json.loads(job["match_reasons"])
        except Exception:
            job["match_reasons"] = [job["match_reasons"]]
    if job.get("skill_gaps"):
        try:
            job["skill_gaps"] = json.loads(job["skill_gaps"])
        except Exception:
            job["skill_gaps"] = [job["skill_gaps"]]
    return job

class StatusUpdate(BaseModel):
    status: str

@app.post("/api/jobs/{job_id}/status")
async def api_update_status(job_id: int, payload: StatusUpdate):
    mark_job_status(job_id, payload.status)
    return {"success": True, "job_id": job_id, "new_status": payload.status}

@app.get("/api/jobs/{job_id}/download/{doc_type}")
async def api_download_doc(job_id: int, doc_type: str):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = None
    if doc_type == "cv":
        file_path = job.get("tailored_cv_path")
    elif doc_type == "cover_letter":
        file_path = job.get("tailored_cl_path")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Tailored {doc_type} file not found on disk")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/pdf"
    )

# --- TRIGGER JOB HUNTING ---
def run_hunt_worker():
    global is_hunting_active
    is_hunting_active = True
    try:
        hunter = JobHunterOrchestrator(log_callback=broadcast_log)
        hunter.run_hunt()
    except Exception as e:
        broadcast_log(f"❌ Error during hunting process: {str(e)}")
    finally:
        is_hunting_active = False
        broadcast_log("🏁 Job hunting worker idle.")

@app.post("/api/hunt")
async def api_trigger_hunt(background_tasks: BackgroundTasks):
    global is_hunting_active
    if is_hunting_active:
        return {"status": "busy", "message": "Job hunting is already in progress!"}

    threading.Thread(target=run_hunt_worker, daemon=True).start()
    return {"status": "started", "message": "Global job hunter launched successfully!"}

@app.get("/api/hunt/stream")
async def api_hunt_stream():
    """Server-Sent Events for real-time log streaming to dashboard terminal."""
    queue = asyncio.Queue()
    log_subscribers.append(queue)

    async def event_generator():
        try:
            # Welcome banner
            yield f"data: {json.dumps({'message': '⚡ Connected to Autonomous Job Hunter Live Stream', 'time': '0'})}\n\n"
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            if queue in log_subscribers:
                log_subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- RECRUITER INBOX TRACKER ---
@app.get("/api/recruiter-replies")
async def api_get_replies(unread_only: bool = False):
    return get_recruiter_replies(unread_only=unread_only)

@app.post("/api/recruiter-replies/{reply_id}/read")
async def api_mark_read(reply_id: int):
    mark_reply_read(reply_id)
    return {"success": True, "reply_id": reply_id}

@app.post("/api/email/check")
async def api_check_email_now():
    tracker = IMAPInboxTracker()
    results = tracker.check_inbox()
    return {"success": True, "count": len(results), "items": results}

@app.post("/api/email/digest")
async def api_send_digest_now():
    top_jobs = get_jobs(min_score=settings.MATCH_THRESHOLD, limit=5)
    success = EmailDigestSender().send_daily_digest(top_jobs)
    return {"success": success, "jobs_sent": len(top_jobs)}

# --- PLAYWRIGHT SAFE AUTOFILL ASSISTANT ---
class AutofillRequest(BaseModel):
    job_id: int

@app.post("/api/playwright/autofill")
async def api_playwright_autofill(req: AutofillRequest):
    job = get_job_by_id(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    assistant = PlaywrightSafeAssistant(headless=False)
    report = assistant.autofill_application(
        job_url=job.get("apply_url"),
        tailored_cv_path=job.get("tailored_cv_path"),
        cover_letter_text=job.get("tailored_cover_letter_text")
    )
    return report

# --- CANDIDATE PROFILE & SETTINGS ---
@app.get("/api/profile")
async def api_get_profile():
    return {
        "profile": settings.get_profile(),
        "target_roles": settings.target_roles,
        "target_locations": settings.target_locations,
        "match_threshold": settings.MATCH_THRESHOLD,
        "has_gemini_key": bool(settings.GEMINI_API_KEY),
        "has_groq_key": bool(settings.GROQ_API_KEY),
        "has_gmail_config": bool(settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD)
    }

class ProfileUpdate(BaseModel):
    target_roles: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    match_threshold: Optional[int] = None
    max_job_age_hours: Optional[int] = None
    auto_pilot_enabled: Optional[bool] = None
    auto_apply_enabled: Optional[bool] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    gmail_user: Optional[str] = None
    gmail_app_password: Optional[str] = None

@app.post("/api/profile")
async def api_update_profile(payload: ProfileUpdate):
    env_path = settings.BASE_DIR / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updates = {}
    if payload.target_roles:
        updates["TARGET_ROLES"] = ", ".join(payload.target_roles)
        settings.TARGET_ROLES_RAW = updates["TARGET_ROLES"]
    if payload.target_locations:
        updates["TARGET_LOCATIONS"] = ", ".join(payload.target_locations)
        settings.TARGET_LOCATIONS_RAW = updates["TARGET_LOCATIONS"]
    if payload.match_threshold is not None:
        updates["MATCH_THRESHOLD"] = str(payload.match_threshold)
        settings.MATCH_THRESHOLD = payload.match_threshold
    if payload.max_job_age_hours is not None:
        updates["MAX_JOB_AGE_HOURS"] = str(payload.max_job_age_hours)
        settings.MAX_JOB_AGE_HOURS = payload.max_job_age_hours
    if payload.auto_pilot_enabled is not None:
        updates["AUTO_PILOT_ENABLED"] = "true" if payload.auto_pilot_enabled else "false"
        settings.AUTO_PILOT_ENABLED = payload.auto_pilot_enabled
        scheduler.toggle_auto_pilot(payload.auto_pilot_enabled)
    if payload.auto_apply_enabled is not None:
        updates["AUTO_APPLY_ENABLED"] = "true" if payload.auto_apply_enabled else "false"
        settings.AUTO_APPLY_ENABLED = payload.auto_apply_enabled
    if payload.gemini_api_key is not None:
        updates["GEMINI_API_KEY"] = payload.gemini_api_key
        settings.GEMINI_API_KEY = payload.gemini_api_key
    if payload.groq_api_key is not None:
        updates["GROQ_API_KEY"] = payload.groq_api_key
        settings.GROQ_MODEL = payload.groq_api_key
    if payload.gmail_user is not None:
        updates["GMAIL_USER"] = payload.gmail_user
        settings.GMAIL_USER = payload.gmail_user
    if payload.gmail_app_password is not None:
        updates["GMAIL_APP_PASSWORD"] = payload.gmail_app_password
        settings.GMAIL_APP_PASSWORD = payload.gmail_app_password

    # Write back to .env
    new_lines = []
    seen = set()
    for line in lines:
        matched = False
        for k, v in updates.items():
            if line.startswith(f"{k}="):
                new_lines.append(f"{k}={v}\n")
                seen.add(k)
                matched = True
                break
        if not matched:
            new_lines.append(line)

    for k, v in updates.items():
        if k not in seen:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return {"success": True, "message": "Settings updated successfully."}
