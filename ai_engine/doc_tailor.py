import json
import requests
from typing import Dict, Any, Optional
from config.settings import settings

class DocumentTailor:
    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.groq_key = settings.GROQ_API_KEY
        self.groq_model = settings.GROQ_MODEL

    def tailor_documents(
        self,
        job_title: str,
        company: str,
        job_description: str,
        cv_text: str
    ) -> Dict[str, Any]:
        """
        Generates tailored ATS resume summary, customized bullet points,
        and personalized cover letter.
        """
        if self.gemini_key and len(self.gemini_key) > 5:
            res = self._tailor_via_gemini(job_title, company, job_description, cv_text)
            if res:
                return res

        if self.groq_key and len(self.groq_key) > 5:
            res = self._tailor_via_groq(job_title, company, job_description, cv_text)
            if res:
                return res

        return self._local_tailor(job_title, company, job_description)

    def _tailor_via_gemini(self, job_title: str, company: str, job_desc: str, cv_text: str) -> Optional[Dict[str, Any]]:
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)

        prompt = f"""
You are an expert Executive Career Coach and ATS Optimization Specialist.
Tailor an ATS-optimized Resume Summary and a bespoke Cover Letter for the following application.

Applicant: {name}
Target Role: {job_title}
Target Company: {company}

Job Description Excerpt:
{job_desc[:2500]}

Applicant CV Details:
{cv_text[:3000]}

Respond with valid JSON ONLY:
{{
  "resume_summary": "<3-4 sentences highly tailored ATS summary emphasizing matching skills>",
  "tailored_bullets": [
    "<Achievement bullet tailored with metrics and matching technologies>",
    "<Achievement bullet 2>",
    "<Achievement bullet 3>",
    "<Achievement bullet 4>"
  ],
  "cover_letter": "<Full tailored cover letter addressed to Hiring Team at {company}, 3-4 professional paragraphs highlighting exact relevance, enthusiasm, and achievements. End with formal sign-off from {name}>"
}}
"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "response_mime_type": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=18)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
        except Exception as e:
            print(f"[DocumentTailor] Gemini tailoring notice: {e}")
        return None

    def _tailor_via_groq(self, job_title: str, company: str, job_desc: str, cv_text: str) -> Optional[Dict[str, Any]]:
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)

        prompt = f"""
Tailor an ATS Resume Summary and Cover Letter for:
Applicant: {name}
Job: {job_title} at {company}
JD: {job_desc[:2000]}
CV: {cv_text[:2500]}

Output JSON ONLY with keys "resume_summary", "tailored_bullets" (array), "cover_letter".
"""
        try:
            headers = {"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.groq_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=14)
            if resp.status_code == 200:
                data = resp.json()
                return json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"[DocumentTailor] Groq tailoring notice: {e}")
        return None

    def _local_tailor(self, job_title: str, company: str, job_desc: str) -> Dict[str, Any]:
        profile = settings.get_profile()
        name = profile.get("name", settings.CANDIDATE_NAME)
        contact = profile.get("contact", {})
        email = contact.get("email", settings.CANDIDATE_EMAIL)
        phone = contact.get("phone", settings.CANDIDATE_PHONE)
        linkedin = contact.get("linkedin", settings.CANDIDATE_LINKEDIN)

        summary = (
            f"Results-driven <strong>Software Engineer & Senior Frontend Specialist</strong> with 4+ years of hands-on experience "
            f"crafting high-performance, accessible, and scalable web applications tailored for <strong>{job_title}</strong> at <strong>{company}</strong>. "
            f"Deeply specialized in <strong>React.js, Next.js, TypeScript, JavaScript (ES6+), Tailwind CSS, and RESTful API integrations</strong>. "
            f"Proven record of slashing page load times by 45% (Lighthouse 95+), increasing organic search traffic by 40%, and delivering "
            f"production features at 2x velocity using AI-accelerated workflows (Cursor AI, Claude 3.7)."
        )

        bullets = [
            f"Architected and deployed responsive web applications and component systems using React.js, Next.js, and TypeScript, directly aligning with {company}'s tech standards.",
            "Conducted Core Web Vitals audits, code splitting, and bundle optimizations, slashing average load times by 45% with 95+ Lighthouse performance scores.",
            "Connected complex third-party RESTful APIs, state stores (Redux Toolkit/Zustand), and payment integrations into seamless UI workflows.",
            "Leveraged AI-assisted development tools (Cursor AI, Claude 3.7) to accelerate feature delivery cycles by 2x while maintaining high code quality."
        ]

        cover_letter = f"""Dear Hiring Team at {company},

I am writing to express my strong enthusiasm for the {job_title} position at {company}. With over 4 years of hands-on software engineering experience specializing in modern frontend architectures (React.js, Next.js, TypeScript, Tailwind CSS) and robust web applications, I am eager to contribute immediately to {company}'s engineering objectives.

Throughout my career, I have focused on building performant, responsive web applications, optimizing Core Web Vitals to achieve 95+ Lighthouse scores, and building seamless RESTful API architectures that scale reliably. In my recent roles, I architected over 20 responsive web applications, cut page load times by 45%, and integrated complex APIs and headless CMS backends.

What excites me most about {company} is your technical vision and commitment to engineering excellence. The requirements outlined in your job description for {job_title} align directly with my hands-on background in modern component design, clean code standards, and agile remote collaboration.

I welcome the opportunity to discuss how my technical skills and proactive engineering approach can help {company} achieve its product milestones. Thank you for your time and consideration.

Sincerely,

{name}
{phone} | {email}
{linkedin}"""

        return {
            "resume_summary": summary,
            "tailored_bullets": bullets,
            "cover_letter": cover_letter
        }
