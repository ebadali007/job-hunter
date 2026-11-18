import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from config.settings import settings

def get_connection() -> sqlite3.Connection:
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        external_id TEXT NOT NULL,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT DEFAULT 'Worldwide Remote',
        is_remote BOOLEAN DEFAULT 1,
        salary TEXT DEFAULT 'Competitive / Undisclosed',
        apply_url TEXT NOT NULL,
        description TEXT NOT NULL,
        tags TEXT DEFAULT '',
        posted_at TEXT,
        match_score INTEGER DEFAULT 0,
        match_reasons TEXT DEFAULT '[]',
        skill_gaps TEXT DEFAULT '[]',
        tailored_cv_path TEXT,
        tailored_cl_path TEXT,
        tailored_cover_letter_text TEXT,
        tailored_resume_summary TEXT,
        status TEXT DEFAULT 'discovered',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, external_id)
    );

    CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(match_score);
    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_company_title ON jobs(company, title);

    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        application_method TEXT DEFAULT 'manual_one_click',
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'applied',
        FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS recruiter_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        sender_email TEXT NOT NULL,
        sender_name TEXT,
        subject TEXT NOT NULL,
        body_snippet TEXT NOT NULL,
        received_at TEXT,
        sentiment TEXT DEFAULT 'interview_invite',
        action_required BOOLEAN DEFAULT 1,
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS hunting_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sources_scraped TEXT DEFAULT '',
        jobs_found INTEGER DEFAULT 0,
        jobs_new INTEGER DEFAULT 0,
        high_matches INTEGER DEFAULT 0,
        status TEXT DEFAULT 'completed',
        log_messages TEXT DEFAULT ''
    );
    """)

    conn.commit()
    conn.close()

def save_job(job: Dict[str, Any]) -> Tuple[int, bool]:
    """Save job into database, skipping duplicate external_id or company+title."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check duplicate by company & title (fuzzy deduplication across sources)
    cursor.execute(
        "SELECT id, match_score FROM jobs WHERE LOWER(company) = LOWER(?) AND LOWER(title) = LOWER(?)",
        (job["company"].strip(), job["title"].strip())
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing["id"], False

    try:
        cursor.execute("""
            INSERT INTO jobs (
                source, external_id, title, company, location, is_remote, salary,
                apply_url, description, tags, posted_at, match_score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("source", "unknown"),
            str(job.get("external_id", "")),
            job.get("title", "Untitled").strip(),
            job.get("company", "Unknown").strip(),
            job.get("location", "Worldwide Remote"),
            1 if job.get("is_remote", True) else 0,
            job.get("salary", "Competitive"),
            job.get("apply_url", ""),
            job.get("description", ""),
            job.get("tags", ""),
            job.get("posted_at", ""),
            int(job.get("match_score", 0)),
            job.get("status", "discovered")
        ))
        conn.commit()
        job_id = cursor.lastrowid
        conn.close()
        return job_id, True
    except sqlite3.IntegrityError:
        # Duplicate source + external_id
        cursor.execute("SELECT id FROM jobs WHERE source = ? AND external_id = ?",
                       (job.get("source"), str(job.get("external_id"))))
        row = cursor.fetchone()
        conn.close()
        return (row["id"] if row else 0), False

def get_jobs(
    status: Optional[str] = None,
    min_score: int = 0,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM jobs WHERE match_score >= ?"
    params: List[Any] = [min_score]

    if status and status != "all":
        query += " AND status = ?"
        params.append(status)

    if search:
        query += " AND (title LIKE ? OR company LIKE ? OR tags LIKE ?)"
        wildcard = f"%{search}%"
        params.extend([wildcard, wildcard, wildcard])

    query += " ORDER BY match_score DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_job_match(
    job_id: int,
    score: int,
    reasons: List[str],
    gaps: List[str],
    tailored_cv_path: Optional[str] = None,
    tailored_cl_path: Optional[str] = None,
    cover_letter_text: Optional[str] = None,
    resume_summary: Optional[str] = None,
    status: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    current_status = row["status"] if row else "discovered"

    if status:
        new_status = status
    elif current_status == "applied":
        new_status = "applied"
    else:
        new_status = "tailored" if tailored_cv_path else ("matched" if score >= 75 else "discovered")

    cursor.execute("""
        UPDATE jobs SET
            match_score = ?,
            match_reasons = ?,
            skill_gaps = ?,
            tailored_cv_path = COALESCE(?, tailored_cv_path),
            tailored_cl_path = COALESCE(?, tailored_cl_path),
            tailored_cover_letter_text = COALESCE(?, tailored_cover_letter_text),
            tailored_resume_summary = COALESCE(?, tailored_resume_summary),
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        score,
        json.dumps(reasons),
        json.dumps(gaps),
        tailored_cv_path,
        tailored_cl_path,
        cover_letter_text,
        resume_summary,
        new_status,
        job_id
    ))
    conn.commit()
    conn.close()

def mark_job_status(job_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, job_id))
    if status == "applied":
        cursor.execute("INSERT INTO applications (job_id, status) VALUES (?, 'applied')", (job_id,))
    conn.commit()
    conn.close()

def save_recruiter_reply(reply: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    # Deduplicate reply by subject and sender
    cursor.execute(
        "SELECT id FROM recruiter_replies WHERE sender_email = ? AND subject = ?",
        (reply["sender_email"], reply["subject"])
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing["id"]

    cursor.execute("""
        INSERT INTO recruiter_replies (
            job_id, sender_email, sender_name, subject, body_snippet,
            received_at, sentiment, action_required, is_read
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        reply.get("job_id"),
        reply.get("sender_email"),
        reply.get("sender_name", ""),
        reply.get("subject"),
        reply.get("body_snippet", ""),
        reply.get("received_at", ""),
        reply.get("sentiment", "interview_invite"),
        1 if reply.get("action_required", True) else 0,
        1 if reply.get("is_read", False) else 0
    ))
    conn.commit()
    reply_id = cursor.lastrowid
    conn.close()
    return reply_id

def get_recruiter_replies(unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if unread_only:
        cursor.execute("SELECT * FROM recruiter_replies WHERE is_read = 0 ORDER BY id DESC LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT * FROM recruiter_replies ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_reply_read(reply_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE recruiter_replies SET is_read = 1 WHERE id = ?", (reply_id,))
    conn.commit()
    conn.close()

def log_hunting_run(
    sources: str,
    found: int,
    new_jobs: int,
    high_matches: int,
    status: str = "completed",
    logs: str = ""
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO hunting_runs (
            sources_scraped, jobs_found, jobs_new, high_matches, status, log_messages
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (sources, found, new_jobs, high_matches, status, logs))
    conn.commit()
    run_id = cursor.lastrowid
    conn.close()
    return run_id

def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM jobs")
    total_jobs = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as high FROM jobs WHERE match_score >= 75")
    high_matches = cursor.fetchone()["high"]

    cursor.execute("SELECT COUNT(*) as tailored FROM jobs WHERE tailored_cv_path IS NOT NULL")
    tailored_count = cursor.fetchone()["tailored"]

    cursor.execute("SELECT COUNT(*) as applied FROM jobs WHERE status = 'applied'")
    applied_count = cursor.fetchone()["applied"]

    cursor.execute("SELECT COUNT(*) as replies FROM recruiter_replies WHERE is_read = 0")
    unread_replies = cursor.fetchone()["replies"]

    cursor.execute("SELECT COUNT(*) as all_replies FROM recruiter_replies")
    total_replies = cursor.fetchone()["all_replies"]

    cursor.execute("SELECT * FROM hunting_runs ORDER BY id DESC LIMIT 1")
    last_run = cursor.fetchone()

    conn.close()
    return {
        "total_jobs": total_jobs,
        "high_matches": high_matches,
        "tailored_count": tailored_count,
        "applied_count": applied_count,
        "unread_replies": unread_replies,
        "total_replies": total_replies,
        "last_run": dict(last_run) if last_run else None
    }
