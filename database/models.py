from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class JobBase(BaseModel):
    source: str
    external_id: str
    title: str
    company: str
    location: Optional[str] = "Worldwide Remote"
    is_remote: bool = True
    salary: Optional[str] = "Competitive / Undisclosed"
    apply_url: str
    description: str
    tags: Optional[str] = ""
    posted_at: Optional[str] = None
    match_score: int = 0
    match_reasons: Optional[str] = "[]"
    skill_gaps: Optional[str] = "[]"
    tailored_cv_path: Optional[str] = None
    tailored_cl_path: Optional[str] = None
    tailored_cover_letter_text: Optional[str] = None
    tailored_resume_summary: Optional[str] = None
    status: str = "discovered"  # discovered, matched, tailored, applied, rejected, archived

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ApplicationCreate(BaseModel):
    job_id: int
    application_method: str = "manual_one_click"
    notes: Optional[str] = ""
    status: str = "applied"

class RecruiterReplyModel(BaseModel):
    id: Optional[int] = None
    job_id: Optional[int] = None
    sender_email: str
    sender_name: Optional[str] = ""
    subject: str
    body_snippet: str
    received_at: Optional[str] = None
    sentiment: str = "interview_invite" # interview_invite, assessment, rejection, query, general
    action_required: bool = True
    is_read: bool = False

class HuntingRunModel(BaseModel):
    id: Optional[int] = None
    run_timestamp: Optional[str] = None
    sources_scraped: str = ""
    jobs_found: int = 0
    jobs_new: int = 0
    high_matches: int = 0
    status: str = "completed"
    log_messages: str = ""
