import os
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from config.settings import settings

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    return re.sub(r'_+', '_', cleaned).strip('_')[:40]

class PDFGenerator:
    def __init__(self):
        self.output_dir = settings.APPLICATIONS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_tailored_pdf_package(
        self,
        company: str,
        job_title: str,
        tailored_data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Generates ATS-optimized Resume PDF and personalized Cover Letter PDF.
        Returns paths: (cv_path, cover_letter_path)
        """
        comp_slug = sanitize_filename(company)
        title_slug = sanitize_filename(job_title)

        cv_filename = f"{comp_slug}_{title_slug}_CV.pdf"
        cl_filename = f"{comp_slug}_{title_slug}_CoverLetter.pdf"

        cv_path = str(self.output_dir / cv_filename)
        cl_path = str(self.output_dir / cl_filename)

        self._build_ats_resume_pdf(cv_path, company, job_title, tailored_data)
        self._build_cover_letter_pdf(cl_path, company, job_title, tailored_data.get("cover_letter", ""))

        return cv_path, cl_path

    def _build_ats_resume_pdf(self, file_path: str, company: str, job_title: str, tailored_data: Dict[str, Any]):
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)
        github = contact.get("github", settings.CANDIDATE_GITHUB)
        portfolio = contact.get("portfolio", settings.CANDIDATE_PORTFOLIO)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0F172A") # Deep Slate
        accent_color = colors.HexColor("#2563EB")  # Modern Blue
        dark_text = colors.HexColor("#1E293B")
        muted_text = colors.HexColor("#64748B")

        title_style = ParagraphStyle(
            'HeaderTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=primary_color,
            alignment=1 # Center
        )

        sub_style = ParagraphStyle(
            'HeaderSub',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=accent_color,
            alignment=1
        )

        contact_style = ParagraphStyle(
            'HeaderContact',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=muted_text,
            alignment=1
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=primary_color,
            spaceAfter=3,
            keepWithNext=True
        )

        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=dark_text
        )

        bullet_style = ParagraphStyle(
            'BulletCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=dark_text,
            leftIndent=14,
            firstLineIndent=-10
        )

        story = []

        # 1. Header
        story.append(Paragraph(name.upper(), title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"Specialized for: {job_title} | {company}", sub_style))
        story.append(Spacer(1, 4))
        contact_line = f"{email}  •  {phone}  •  {location}"
        story.append(Paragraph(contact_line, contact_style))
        social_items = []
        if linkedin:
            social_items.append(f"LinkedIn: {linkedin}")
        if github:
            social_items.append(f"GitHub: {github}")
        if portfolio:
            social_items.append(f"Portfolio: {portfolio}")
        if social_items:
            story.append(Paragraph("  |  ".join(social_items), contact_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=8))

        # 2. Tailored ATS Summary
        story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
        summary_text = tailored_data.get("resume_summary") or profile.get("summary", "")
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 8))

        # 3. Core Technical Skills
        story.append(Paragraph("TECHNICAL SKILLS & CORE COMPETENCIES", section_heading))
        skills_dict = profile.get("skills", {})
        skill_lines = []
        if skills_dict.get("frontend"):
            skill_lines.append(f"<b>Frontend:</b> {', '.join(skills_dict['frontend'])}")
        if skills_dict.get("cms_and_custom_web"):
            skill_lines.append(f"<b>CMS & Custom Web:</b> {', '.join(skills_dict['cms_and_custom_web'])}")
        if skills_dict.get("state_and_apis"):
            skill_lines.append(f"<b>State & APIs:</b> {', '.join(skills_dict['state_and_apis'])}")
        if skills_dict.get("ai_workflows_and_devops"):
            skill_lines.append(f"<b>AI Workflows & DevOps:</b> {', '.join(skills_dict['ai_workflows_and_devops'])}")
        if skills_dict.get("languages"):
            skill_lines.append(f"<b>Languages:</b> {', '.join(skills_dict['languages'])}")
        if not skill_lines:
            for k, v in skills_dict.items():
                if isinstance(v, list) and v:
                    skill_lines.append(f"<b>{k.replace('_', ' ').title()}:</b> {', '.join(v)}")
        skills_text = "<br/>".join(skill_lines)
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 8))

        # 4. Tailored Role Highlights
        tailored_bullets = tailored_data.get("tailored_bullets", [])
        if tailored_bullets:
            story.append(Paragraph(f"KEY ALIGNMENT & ACHIEVEMENTS FOR {company.upper()}", section_heading))
            for b in tailored_bullets:
                story.append(Paragraph(f"• <b>Impact:</b> {b}", bullet_style))
                story.append(Spacer(1, 2))
            story.append(Spacer(1, 6))

        # 5. Professional Experience
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_heading))
        experiences = profile.get("experience", [])
        for exp in experiences:
            exp_header = f"<b>{exp.get('role')}</b> — <i>{exp.get('company')}</i> ({exp.get('period')}) | {exp.get('location')}"
            story.append(Paragraph(exp_header, body_style))
            story.append(Spacer(1, 2))
            for highlight in exp.get("highlights", []):
                story.append(Paragraph(f"• {highlight}", bullet_style))
                story.append(Spacer(1, 1.5))
            story.append(Spacer(1, 4))

        # 6. Education & Certifications
        story.append(Paragraph("EDUCATION & CERTIFICATIONS", section_heading))
        education = profile.get("education", [])
        for edu in education:
            edu_time = edu.get('year') or edu.get('period', '')
            time_part = f" ({edu_time})" if edu_time else ""
            edu_str = f"• <b>{edu.get('degree')}</b>, {edu.get('institution')}{time_part}"
            story.append(Paragraph(edu_str, bullet_style))
        certs = profile.get("certifications", [])
        if certs:
            certs_str = f"• <b>Certifications:</b> {', '.join(certs)}"
            story.append(Paragraph(certs_str, bullet_style))

        doc.build(story)

    def _build_cover_letter_pdf(self, file_path: str, company: str, job_title: str, letter_body: str):
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)

        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=48,
            bottomMargin=48
        )

        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0F172A")
        accent_color = colors.HexColor("#2563EB")
        dark_text = colors.HexColor("#1E293B")
        muted_text = colors.HexColor("#64748B")

        name_style = ParagraphStyle(
            'CLName',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=primary_color
        )

        sub_style = ParagraphStyle(
            'CLContact',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=muted_text
        )

        meta_style = ParagraphStyle(
            'CLMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=dark_text
        )

        subject_style = ParagraphStyle(
            'CLSubject',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=15,
            textColor=accent_color
        )

        para_style = ParagraphStyle(
            'CLPara',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=15,
            textColor=dark_text,
            spaceAfter=10
        )

        story = []

        # Top Letterhead
        story.append(Paragraph(name, name_style))
        story.append(Paragraph(f"{email}  •  {phone}  •  {location}", sub_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=14))

        # Date & Recipient
        import datetime
        today_str = datetime.datetime.now().strftime("%B %d, %Y")
        recipient_block = f"""
        {today_str}<br/><br/>
        <b>Hiring Team & Engineering Leadership</b><br/>
        {company}<br/>
        """
        story.append(Paragraph(recipient_block, meta_style))
        story.append(Spacer(1, 6))

        # Subject Line
        story.append(Paragraph(f"RE: Application for {job_title} position", subject_style))
        story.append(Spacer(1, 12))

        # Letter paragraphs
        paragraphs = letter_body.strip().split("\n\n")
        for p in paragraphs:
            cleaned_p = p.replace("\n", " ").strip()
            if cleaned_p:
                story.append(Paragraph(cleaned_p, para_style))

        doc.build(story)
