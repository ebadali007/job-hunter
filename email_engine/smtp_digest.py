import smtplib
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Dict, Any, Optional
from config.settings import settings

class EmailDigestSender:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.username = settings.GMAIL_USER
        self.password = settings.GMAIL_APP_PASSWORD
        # Send to both candidate email and notify email (no duplicates)
        recips = []
        for e in [settings.CANDIDATE_EMAIL, settings.NOTIFY_EMAIL, settings.GMAIL_USER]:
            if e and e.strip() and e.strip() not in recips:
                recips.append(e.strip())
        self.recipients = recips
        self.recipient = ", ".join(recips)

    def is_configured(self) -> bool:
        return bool(self.username and self.password and len(self.password) >= 16)

    def send_daily_digest(self, top_jobs: List[Dict[str, Any]]) -> bool:
        """
        Sends Daily Global Job Report email with HTML summary and attached CVs.
        """
        if not self.is_configured():
            print("[EmailDigestSender] Gmail credentials not set in .env. Skipping email dispatch.")
            return False

        if not top_jobs:
            print("[EmailDigestSender] No matched jobs to report today.")
            return False

        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"🎯 Global Job Hunter: {len(top_jobs)} Matched Opportunities Ready for You!"
        msg["From"] = f"Global Job Hunter AI <{self.username}>"
        msg["To"] = self.recipient

        html_body = self._build_html_report(top_jobs)
        msg.attach(MIMEText(html_body, "html"))

        # Attach tailored PDFs for top 3 matches
        attached_count = 0
        for job in top_jobs[:3]:
            cv_path = job.get("tailored_cv_path")
            cl_path = job.get("tailored_cl_path")
            for file_path in [cv_path, cl_path]:
                if file_path and os.path.exists(file_path) and attached_count < 6:
                    try:
                        with open(file_path, "rb") as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                            msg.attach(part)
                            attached_count += 1
                    except Exception as ex:
                        print(f"[EmailDigestSender] Warning attaching file {file_path}: {ex}")

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg, to_addrs=self.recipients)
            print(f"[EmailDigestSender] Daily report successfully sent to {self.recipient} with {attached_count} attachments.")
            return True
        except Exception as e:
            print(f"[EmailDigestSender] Failed to send email: {e}")
            return False

    def send_recruiter_alert(self, reply: Dict[str, Any]) -> bool:
        """Sends instant high-priority alert when an interview/recruiter email is detected."""
        if not self.is_configured():
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 URGENT: Recruiter Reply / Interview Invitation from {reply.get('sender_name') or reply.get('sender_email')}"
        msg["From"] = f"Job Hunter Alert <{self.username}>"
        msg["To"] = self.recipient

        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#0f172a; color:#f8fafc; padding:24px;">
            <div style="max-width:600px; margin:0 auto; background:#1e293b; border-radius:12px; padding:24px; border:1px solid #334155;">
                <h2 style="color:#38bdf8; margin-top:0;">⚡ Recruiter Response Detected!</h2>
                <p style="font-size:15px; color:#94a3b8;">A potential interview invitation or recruiter message was received:</p>
                
                <div style="background:#0f172a; padding:16px; border-radius:8px; border-left:4px solid #38bdf8; margin:20px 0;">
                    <p style="margin:4px 0;"><b>From:</b> {reply.get('sender_name')} &lt;{reply.get('sender_email')}&gt;</p>
                    <p style="margin:4px 0;"><b>Subject:</b> {reply.get('subject')}</p>
                    <p style="margin:4px 0;"><b>Classification:</b> <span style="background:#0369a1; padding:2px 8px; border-radius:4px; font-size:12px;">{reply.get('sentiment', '').upper()}</span></p>
                    <hr style="border:0; border-top:1px solid #334155; margin:12px 0;">
                    <p style="margin:4px 0; font-size:14px; color:#cbd5e1;"><b>Snippet:</b><br/>{reply.get('body_snippet')}</p>
                </div>

                <a href="http://localhost:{settings.PORT}" style="display:inline-block; background:#2563eb; color:#ffffff; padding:10px 20px; border-radius:6px; text-decoration:none; font-weight:600;">Open Dashboard to Review</a>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg, to_addrs=self.recipients)
            return True
        except Exception as e:
            print(f"[EmailDigestSender] Recruiter alert send error: {e}")
            return False

    def _build_html_report(self, jobs: List[Dict[str, Any]]) -> str:
        job_cards_html = ""
        for job in jobs:
            reasons = job.get("match_reasons", "[]")
            if isinstance(reasons, str):
                try:
                    reasons = json.loads(reasons)
                except Exception:
                    reasons = [reasons]
            reasons_html = "".join([f"<li style='margin-bottom:4px;'>{r}</li>" for r in (reasons or [])[:3]])

            score = job.get("match_score", 0)
            score_color = "#10b981" if score >= 85 else "#3b82f6"

            job_cards_html += f"""
            <div style="background:#1e293b; border:1px solid #334155; border-radius:10px; padding:20px; margin-bottom:18px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                    <div>
                        <h3 style="margin:0; font-size:18px; color:#f8fafc;">{job.get('title')}</h3>
                        <p style="margin:4px 0 0 0; color:#38bdf8; font-weight:600; font-size:14px;">{job.get('company')} • <span style="color:#94a3b8; font-weight:normal;">{job.get('location')}</span></p>
                    </div>
                    <div style="background:{score_color}; color:#ffffff; font-weight:bold; font-size:14px; padding:6px 12px; border-radius:20px; display:inline-block;">
                        {score}% Match
                    </div>
                </div>

                <p style="margin:8px 0; font-size:13px; color:#a5b4fc;">💰 <b>Salary:</b> {job.get('salary', 'Competitive')}</p>

                <div style="background:#0f172a; border-radius:6px; padding:12px 16px; margin:12px 0;">
                    <p style="margin:0 0 6px 0; font-size:12px; font-weight:bold; color:#94a3b8; text-transform:uppercase;">AI Match Highlights:</p>
                    <ul style="margin:0; padding-left:18px; font-size:13px; color:#cbd5e1;">
                        {reasons_html}
                    </ul>
                </div>

                <div style="margin-top:14px;">
                    <a href="{job.get('apply_url')}" style="background:#2563eb; color:#ffffff; text-decoration:none; padding:8px 16px; border-radius:6px; font-size:13px; font-weight:600; display:inline-block; margin-right:8px;">
                        Direct Apply Link →
                    </a>
                </div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color:#0b1120; color:#f8fafc; margin:0; padding:24px;">
            <div style="max-width:700px; margin:0 auto;">
                <div style="text-align:center; padding-bottom:24px; border-bottom:1px solid #334155; margin-bottom:24px;">
                    <h1 style="color:#38bdf8; margin:0 0 8px 0; font-size:24px;">🎯 Global Job Hunter AI Digest</h1>
                    <p style="color:#94a3b8; margin:0; font-size:14px;">Curated high-match opportunities tailored to your profile.</p>
                </div>

                <div style="margin-bottom:24px;">
                    {job_cards_html}
                </div>

                <div style="text-align:center; padding:18px; color:#64748b; font-size:12px; border-top:1px solid #1e293b;">
                    Autonomous Global Job Hunter • Running locally on your PC
                </div>
            </div>
        </body>
        </html>
        """
