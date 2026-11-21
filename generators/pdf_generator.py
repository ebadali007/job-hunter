import os
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from jinja2 import Environment, FileSystemLoader

# ReportLab fallbacks
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from config.settings import settings

def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    return re.sub(r'_+', '_', cleaned).strip('_')[:40]

class PDFGenerator:
    def __init__(self):
        self.output_dir = settings.APPLICATIONS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = settings.BASE_DIR / "generators" / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def generate_tailored_pdf_package(
        self,
        company: str,
        job_title: str,
        tailored_data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Generates bespoke Resume PDF using user's modern Ebad Ali layout
        and personalized Cover Letter PDF tailored to the job description.
        Returns paths: (cv_path, cover_letter_path)
        """
        comp_slug = sanitize_filename(company)
        title_slug = sanitize_filename(job_title)

        cv_filename = f"{comp_slug}_{title_slug}_CV.pdf"
        cl_filename = f"{comp_slug}_{title_slug}_CoverLetter.pdf"

        cv_path = str(self.output_dir / cv_filename)
        cl_path = str(self.output_dir / cl_filename)

        # 1. Generate Modern Tailored Resume PDF
        self._build_resume_pdf(cv_path, company, job_title, tailored_data)

        # 2. Generate Modern Tailored Cover Letter PDF
        self._build_cover_letter_pdf(cl_path, company, job_title, tailored_data.get("cover_letter", ""))

        return cv_path, cl_path

    def _build_resume_pdf(self, file_path: str, company: str, job_title: str, tailored_data: Dict[str, Any]):
        """Try high-fidelity HTML->Playwright rendering first; fallback to ReportLab if needed."""
        try:
            self._render_html_cv(file_path, company, job_title, tailored_data)
            print(f"[PDFGenerator] Generated modern HTML/Playwright CV: {file_path}")
        except Exception as e:
            print(f"[PDFGenerator] Playwright CV render notice ({e}), falling back to ReportLab...")
            self._build_ats_resume_pdf_reportlab(file_path, company, job_title, tailored_data)

    def _build_cover_letter_pdf(self, file_path: str, company: str, job_title: str, letter_body: str):
        """Try high-fidelity HTML->Playwright rendering first; fallback to ReportLab if needed."""
        try:
            self._render_html_cover_letter(file_path, company, job_title, letter_body)
            print(f"[PDFGenerator] Generated modern HTML/Playwright Cover Letter: {file_path}")
        except Exception as e:
            print(f"[PDFGenerator] Playwright Cover Letter render notice ({e}), falling back to ReportLab...")
            self._build_cover_letter_pdf_reportlab(file_path, company, job_title, letter_body)

    def _render_html_cv(self, file_path: str, company: str, job_title: str, tailored_data: Dict[str, Any]):
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)
        github = contact.get("github", settings.CANDIDATE_GITHUB)
        portfolio = contact.get("portfolio", settings.CANDIDATE_PORTFOLIO)

        # Tailored summary or fallback
        summary = tailored_data.get("resume_summary") or profile.get("summary", "")

        # Prepare experience with tailored bullets injected
        experience = list(profile.get("experience", []))
        tailored_bullets = tailored_data.get("tailored_bullets", [])
        if tailored_bullets and len(experience) > 0:
            exp_copy = dict(experience[0])
            original_highlights = exp_copy.get("highlights", [])
            merged_highlights = []
            for b in tailored_bullets:
                clean_b = b.strip()
                if not clean_b.startswith("<strong>") and ":" in clean_b:
                    prefix, rest = clean_b.split(":", 1)
                    clean_b = f"<strong>{prefix}:</strong>{rest}"
                merged_highlights.append(clean_b)
            merged_highlights.extend(original_highlights[:4])
            exp_copy["highlights"] = merged_highlights
            experience[0] = exp_copy

        skills = profile.get("skills", {
            "frontend": ["React.js", "Next.js", "TypeScript", "JavaScript (ES6+)", "HTML5 & CSS3", "Tailwind CSS", "Bootstrap"],
            "cms_and_custom_web": ["WordPress Dev", "Custom PHP Themes", "WooCommerce", "Headless CMS", "Elementor Pro"],
            "state_and_apis": ["RESTful APIs", "Redux Toolkit", "Zustand", "Axios / Fetch", "JSON Data"],
            "ai_workflows_and_devops": ["Git & GitHub", "Cursor AI", "Claude 3.7", "Antigravity", "Vercel / Netlify", "VS Code"],
            "engineering_practices": ["Core Web Vitals", "Technical SEO", "Responsive UI", "Performance Tuning"],
            "languages": ["English (Professional Fluent)", "Urdu (Native)"],
            "collaboration_tools": ["Slack", "Jira", "Loom", "Agile/Scrum"]
        })

        projects = profile.get("projects", [
            {
                "name": "AI-Accelerated Web Application Dashboard",
                "tech_stack": "React.js, TypeScript, Tailwind CSS, REST APIs, Git, Vercel",
                "description": "Designed and deployed an interactive web application dashboard featuring dynamic data charts, theme switching, and real-time state management."
            },
            {
                "name": "E-Commerce Headless Storefront & Custom CMS",
                "tech_stack": "WordPress, WooCommerce, PHP, JavaScript, CSS3, REST API",
                "description": "Architected a custom WooCommerce platform with bespoke PHP theme templates, AJAX live search, payment gateway integrations, and load speeds under 1.2s."
            }
        ])

        education = profile.get("education", [
            {
                "degree": "BS in Software Engineering (In Progress)",
                "period": "2023 – Present | Expected 2027",
                "institution": "SMI University, Karachi, Pakistan",
                "details": "Relevant Coursework: Data Structures & Algorithms, Web Engineering, Object-Oriented Programming (OOP), Database Systems, Software Architecture."
            }
        ])

        template = self.jinja_env.get_template("ebad_ali_cv.html")
        rendered_html = template.render(
            name=name,
            title=profile.get("title", "Software Engineer & Senior Frontend Specialist"),
            target_company=company,
            target_role=job_title,
            location=location,
            phone=phone,
            email=email,
            linkedin=linkedin,
            github=github,
            portfolio=portfolio,
            summary=summary,
            experience=experience,
            skills=skills,
            projects=projects,
            education=education
        )

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            page = browser.new_page()
            page.set_content(rendered_html, wait_until='networkidle')
            page.pdf(
                path=file_path,
                format='A4',
                print_background=True,
                prefer_css_page_size=True,
                margin={'top': '0mm', 'right': '0mm', 'bottom': '0mm', 'left': '0mm'}
            )
            browser.close()

    def _render_html_cover_letter(self, file_path: str, company: str, job_title: str, letter_body: str):
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)
        github = contact.get("github", settings.CANDIDATE_GITHUB)
        portfolio = contact.get("portfolio", settings.CANDIDATE_PORTFOLIO)

        raw_paras = letter_body.strip().split("\n\n")
        paras = []
        for p in raw_paras:
            clean = p.replace("\n", " ").strip()
            if clean:
                paras.append(clean)

        if not paras:
            paras = [
                f"I am writing to express my strong enthusiasm for the {job_title} role at {company}. With 4+ years of hands-on software engineering experience specializing in React.js, Next.js, TypeScript, and high-performance web systems, I am confident in my ability to immediately accelerate your team's objectives.",
                f"Throughout my career, I have focused on building performant, responsive web applications, optimizing Core Web Vitals to achieve 95+ Lighthouse scores, and building seamless RESTful API architectures.",
                f"I welcome the opportunity to discuss how my technical expertise aligns with {company}'s roadmap. Thank you for your consideration."
            ]

        today_str = datetime.datetime.now().strftime("%B %d, %Y")
        template = self.jinja_env.get_template("ebad_ali_cover_letter.html")
        rendered_html = template.render(
            name=name,
            title=profile.get("title", "Software Engineer & Senior Frontend Specialist"),
            target_company=company,
            target_role=job_title,
            location=location,
            phone=phone,
            email=email,
            linkedin=linkedin,
            github=github,
            portfolio=portfolio,
            date_str=today_str,
            letter_paragraphs=paras
        )

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            page = browser.new_page()
            page.set_content(rendered_html, wait_until='networkidle')
            page.pdf(
                path=file_path,
                format='A4',
                print_background=True,
                prefer_css_page_size=True,
                margin={'top': '15mm', 'right': '15mm', 'bottom': '15mm', 'left': '15mm'}
            )
            browser.close()

    def _build_ats_resume_pdf_reportlab(self, file_path: str, company: str, job_title: str, tailored_data: Dict[str, Any]):
        """ReportLab Fallback in case Chromium is unavailable."""
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)
        github = contact.get("github", settings.CANDIDATE_GITHUB)
        portfolio = contact.get("portfolio", settings.CANDIDATE_PORTFOLIO)

        doc = SimpleDocTemplate(file_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0F172A")
        accent_color = colors.HexColor("#2563EB")
        dark_text = colors.HexColor("#1E293B")
        muted_text = colors.HexColor("#64748B")

        title_style = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=primary_color, alignment=1)
        sub_style = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=accent_color, alignment=1)
        contact_style = ParagraphStyle('HeaderContact', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, textColor=muted_text, alignment=1)
        section_heading = ParagraphStyle('SectionHeading', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=primary_color, spaceAfter=3, keepWithNext=True)
        body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=dark_text)
        bullet_style = ParagraphStyle('BulletCustom', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, textColor=dark_text, leftIndent=14, firstLineIndent=-10)

        story = []
        story.append(Paragraph(name.upper(), title_style))
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"Specialized for: {job_title} | {company}", sub_style))
        story.append(Spacer(1, 4))
        contact_line = f"{email}  •  {phone}  •  {location}"
        story.append(Paragraph(contact_line, contact_style))
        social_items = []
        if linkedin: social_items.append(f"LinkedIn: {linkedin}")
        if github: social_items.append(f"GitHub: {github}")
        if portfolio: social_items.append(f"Portfolio: {portfolio}")
        if social_items:
            story.append(Paragraph("  |  ".join(social_items), contact_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=8))

        story.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
        summary_text = tailored_data.get("resume_summary") or profile.get("summary", "")
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 8))

        tailored_bullets = tailored_data.get("tailored_bullets", [])
        if tailored_bullets:
            story.append(Paragraph(f"KEY ALIGNMENT & ACHIEVEMENTS FOR {company.upper()}", section_heading))
            for b in tailored_bullets:
                story.append(Paragraph(f"• <b>Impact:</b> {b}", bullet_style))
                story.append(Spacer(1, 2))
            story.append(Spacer(1, 6))

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

        story.append(Paragraph("EDUCATION & CERTIFICATIONS", section_heading))
        education = profile.get("education", [])
        for edu in education:
            edu_time = edu.get('year') or edu.get('period', '')
            time_part = f" ({edu_time})" if edu_time else ""
            edu_str = f"• <b>{edu.get('degree')}</b>, {edu.get('institution')}{time_part}"
            story.append(Paragraph(edu_str, bullet_style))

        doc.build(story)

    def _build_cover_letter_pdf_reportlab(self, file_path: str, company: str, job_title: str, letter_body: str):
        """ReportLab Fallback in case Chromium is unavailable."""
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        location = contact.get("location", settings.CANDIDATE_LOCATION)

        doc = SimpleDocTemplate(file_path, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=48, bottomMargin=48)
        styles = getSampleStyleSheet()
        primary_color = colors.HexColor("#0F172A")
        accent_color = colors.HexColor("#2563EB")
        dark_text = colors.HexColor("#1E293B")
        muted_text = colors.HexColor("#64748B")

        name_style = ParagraphStyle('CLName', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=primary_color)
        sub_style = ParagraphStyle('CLContact', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=muted_text)
        meta_style = ParagraphStyle('CLMeta', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, textColor=dark_text)
        subject_style = ParagraphStyle('CLSubject', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10.5, leading=15, textColor=accent_color)
        para_style = ParagraphStyle('CLPara', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=15, textColor=dark_text, spaceAfter=10)

        story = []
        story.append(Paragraph(name, name_style))
        story.append(Paragraph(f"{email}  •  {phone}  •  {location}", sub_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=14))

        today_str = datetime.datetime.now().strftime("%B %d, %Y")
        recipient_block = f"{today_str}<br/><br/><b>Hiring Team & Engineering Leadership</b><br/>{company}<br/>"
        story.append(Paragraph(recipient_block, meta_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph(f"RE: Application for {job_title} position", subject_style))
        story.append(Spacer(1, 12))

        paragraphs = letter_body.strip().split("\n\n")
        for p in paragraphs:
            cleaned_p = p.replace("\n", " ").strip()
            if cleaned_p:
                story.append(Paragraph(cleaned_p, para_style))

        doc.build(story)
