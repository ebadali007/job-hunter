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
            f"Results-driven Mid-to-Senior Full-Stack & Mobile Engineer with 5+ years of production experience, "
            f"specializing in building scalable, resilient applications tailored for {job_title} responsibilities at {company}. "
            f"Deeply proficient across modern TypeScript/React/Next.js architectures, cross-platform mobile apps (Flutter/React Native), "
            f"and high-throughput Python/Node.js microservices. Proven success optimizing system latency by 85% and maintaining 99.9% uptime."
        )

        bullets = [
            f"Engineered high-performance web and mobile systems serving 150k+ active users, closely matching {company}'s tech demands.",
            "Architected scalable RESTful & GraphQL backend microservices in Python (FastAPI) and Node.js with PostgreSQL and Redis caching.",
            "Delivered pixel-perfect, accessible user interfaces utilizing Next.js, React, TypeScript, and Tailwind CSS with 95+ Lighthouse scores.",
            "Established robust CI/CD automation and containerized deployments using Docker and GitHub Actions, slashing release cycles by 40%."
        ]

        cover_letter = f"""Dear Hiring Team at {company},

I am writing to express my strong enthusiasm for the {job_title} position at {company}. With over 5 years of hands-on software engineering experience specializing in Full-Stack web architectures (TypeScript, React, Next.js, Python, Node.js) and cross-platform mobile development (Flutter and React Native), I am confident that my technical expertise and problem-solving mindset make me an immediate contributor to your team.

Throughout my career, I have focused on building performant, user-centric software that scales reliably. At Apex Global Technologies, I architected SaaS platforms serving over 150,000 monthly active users and engineered production mobile applications with real-time sync that lifted user retention by 42%. In addition, I successfully restructured database and caching layers, cutting API response times from 320ms down to 45ms.

What excites me most about {company} is your commitment to technical innovation and engineering excellence. The requirements outlined in your job description for {job_title} align directly with my hands-on background in modern frontend frameworks, cloud deployment pipelines, and robust backend engineering.

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
