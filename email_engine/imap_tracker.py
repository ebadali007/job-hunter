import imaplib
import email
from email.header import decode_header
import re
import html
from typing import List, Dict, Any, Optional
from config.settings import settings
from database.db import save_recruiter_reply
from email_engine.smtp_digest import EmailDigestSender

IGNORED_DOMAINS = [
    "instagram.com", "facebookmail.com", "facebook.com", "meta.com",
    "twitter.com", "x.com", "tiktok.com", "youtube.com", "pinterest.com",
    "redditmail.com", "reddit.com", "quora.com", "medium.com", "threads.net",
    "spotify.com", "netflix.com", "daraz.pk", "careem.com", "uber.com",
    "amazon.com", "aliexpress.com", "ebay.com", "paypal.com",
    "accounts.google.com"
]

RECRUITER_KEYWORDS = {
    "interview_invite": [
        r"\binterview\b", r"\binvitation\b", r"\bschedule a call\b", r"\bspeak with you\b",
        r"\bchat about your application\b", r"calendly\.com", r"zoom\.(us|com)",
        r"meet\.google\.com", r"\bnext round\b", r"\bhiring manager\b", r"\bphone screen\b"
    ],
    "assessment": [
        r"\btechnical assessment\b", r"\bcoding challenge\b", r"hackerrank", r"coderpad",
        r"\btake-home\b", r"\btake home assignment\b", r"\bonline test\b"
    ],
    "offer": [
        r"\boffer letter\b", r"\bformal offer\b", r"\bpleased to offer\b"
    ],
    "rejection": [
        r"\bunfortunately\b.*\b(not moving forward|other candidates|decision)\b",
        r"\bnot moving forward\b", r"\bregret to inform\b", r"\bnot selected at this time\b"
    ]
}

JOB_CONTEXT_PATTERNS = [
    r"\byour application\b", r"\bjob application\b", r"\byour resume\b",
    r"\byour cv\b", r"\byour candidature\b", r"\bjob opportunity\b",
    r"\bposition of\b", r"\bwe received your application\b",
    r"\bthank you for applying\b", r"\bapplication for\b", r"\brecruiter\b",
    r"\bhiring team\b", r"\btalent acquisition\b"
]

def clean_html_text(raw_html: str) -> str:
    """Removes HTML tags, CSS, scripts, and converts entities to clean plain text."""
    if not raw_html:
        return ""
    # Strip script and style blocks
    cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    # Unescape HTML entities (&amp;, &quot;, etc.)
    cleaned = html.unescape(cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class IMAPInboxTracker:
    def __init__(self):
        self.imap_server = "imap.gmail.com"
        self.username = settings.GMAIL_USER
        self.password = settings.GMAIL_APP_PASSWORD

    def is_configured(self) -> bool:
        return bool(self.username and self.password and len(self.password) >= 16)

    def check_inbox(self) -> List[Dict[str, Any]]:
        """
        Inspects Gmail inbox for authentic recruiter replies and interview invitations.
        Filters out social media, marketing, and un-related emails.
        """
        if not self.is_configured():
            print("[IMAPTracker] Gmail credentials not configured. Skipping IMAP scan.")
            return []

        detected_replies: List[Dict[str, Any]] = []

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server)
            mail.login(self.username, self.password)
            mail.select("inbox")

            # Search unseen messages or recent messages from last 3 days
            status, messages = mail.search(None, '(UNSEEN)')
            msg_ids = messages[0].split()

            if not msg_ids:
                from datetime import datetime, timedelta
                since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
                status, messages = mail.search(None, f'(SINCE "{since_date}")')
                all_ids = messages[0].split()
                msg_ids = all_ids[-20:] if len(all_ids) > 20 else all_ids

            # Inspect recent 15 messages quickly
            for num in reversed(msg_ids[-15:]):
                try:
                    res, header_data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                    raw_header = header_data[0][1].decode("utf-8", errors="ignore") if header_data and header_data[0] else ""

                    res, msg_data = mail.fetch(num, "(BODY.PEEK[TEXT]<0.2500>)")
                    raw_body = msg_data[0][1].decode("utf-8", errors="ignore") if msg_data and msg_data[0] else ""

                    # Extract Subject, From, Date
                    subject_match = re.search(r'Subject:\s*(.*)', raw_header, re.IGNORECASE)
                    from_match = re.search(r'From:\s*(.*)', raw_header, re.IGNORECASE)
                    date_match = re.search(r'Date:\s*(.*)', raw_header, re.IGNORECASE)

                    raw_subject = subject_match.group(1).strip() if subject_match else ""
                    raw_from = from_match.group(1).strip() if from_match else ""
                    date_str = date_match.group(1).strip() if date_match else ""

                    parsed = self._classify_message(raw_subject, raw_from, date_str, raw_body)
                    if parsed:
                        reply_id = save_recruiter_reply(parsed)
                        parsed["id"] = reply_id
                        detected_replies.append(parsed)
                        if parsed["sentiment"] in ("interview_invite", "offer", "assessment"):
                            EmailDigestSender().send_recruiter_alert(parsed)
                except Exception as inner_e:
                    continue

            mail.close()
            mail.logout()
            print(f"[IMAPTracker] Scan completed. Discovered {len(detected_replies)} recruiter communications.")

        except Exception as e:
            print(f"[IMAPTracker] IMAP connection notice: {e}")

        return detected_replies

    def _classify_message(self, raw_subject: str, sender: str, date_str: str, raw_body: str) -> Optional[Dict[str, Any]]:
        raw_subject = self._decode_str(raw_subject)
        sender = self._decode_str(sender)

        # Parse sender email
        sender_email = sender
        sender_name = ""
        match = re.search(r'(.*)<(.*)>', sender)
        if match:
            sender_name = match.group(1).strip().strip('"')
            sender_email = match.group(2).strip()

        sender_email_lower = sender_email.lower()

        # 1. Reject self-alerts and candidate's own email
        if self.username and self.username.lower() in sender_email_lower:
            return None

        # 2. Reject social media, marketing, and non-recruiter domains
        for domain in IGNORED_DOMAINS:
            if domain in sender_email_lower:
                return None

        # Clean HTML into pure readable text
        clean_body = clean_html_text(raw_body)
        combined = f"{raw_subject} {clean_body}".lower()

        # 3. Sentiment classification using regex word boundaries
        sentiment = None
        for category, patterns in RECRUITER_KEYWORDS.items():
            for pat in patterns:
                if re.search(pat, combined, re.IGNORECASE):
                    sentiment = category
                    break
            if sentiment:
                break

        # 4. If no specific category matched, verify if genuine job/application context exists
        if not sentiment:
            has_job_context = any(re.search(pat, combined, re.IGNORECASE) for pat in JOB_CONTEXT_PATTERNS)
            if has_job_context:
                sentiment = "general"
            else:
                return None

        # 5. Build clean, human-readable snippet (up to 250 chars)
        clean_snippet = clean_body[:250].strip()
        if not clean_snippet:
            clean_snippet = raw_subject

        return {
            "sender_email": sender_email,
            "sender_name": sender_name or sender_email,
            "subject": raw_subject,
            "body_snippet": clean_snippet,
            "received_at": date_str,
            "sentiment": sentiment,
            "action_required": sentiment in ("interview_invite", "assessment", "offer"),
            "is_read": False
        }

    def _decode_str(self, val: str) -> str:
        if not val:
            return ""
        decoded_list = decode_header(val)
        result = []
        for content, encoding in decoded_list:
            if isinstance(content, bytes):
                try:
                    result.append(content.decode(encoding or "utf-8", errors="ignore"))
                except Exception:
                    result.append(content.decode("utf-8", errors="ignore"))
            else:
                result.append(str(content))
        return "".join(result)
