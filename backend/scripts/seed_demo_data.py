import hashlib
import json
import os
import sys
from datetime import datetime, UTC
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.db import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models import (
    CandidateProfile,
    EmbeddingRecord,
    Job,
    JobRequirement,
    JobVersion,
    Organization,
    OrganizationMembership,
    Resume,
    ResumeConsent,
    ResumeExtraction,
    ResumeVersion,
    User,
    utc_now,
)
from app.services.search import initialize_search_index, upsert_resume_search


def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    initialize_search_index()

    with SessionLocal() as db:
        # 1. Admin
        admin_email = "admin@tandem.test"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                display_name="Platform Admin",
                password_hash=hash_password("AdminPassword123!"),
                role="admin",
            )
            db.add(admin)
            print(f"Created admin: {admin_email}")

        # 2. Organization
        org = db.query(Organization).filter(Organization.name == "Northstar Labs").first()
        if not org:
            org = Organization(name="Northstar Labs", status="verified")
            db.add(org)
            db.flush()
            print(f"Created organization: {org.name}")

        # 3. Recruiter
        recruiter_email = "recruiter@example.com"
        recruiter = db.query(User).filter(User.email == recruiter_email).first()
        if not recruiter:
            recruiter = User(
                email=recruiter_email,
                display_name="Maya Lin",
                password_hash=hash_password("Password123456!"),
                role="recruiter",
            )
            db.add(recruiter)
            db.flush()
            print(f"Created recruiter: {recruiter_email}")

        membership = db.query(OrganizationMembership).filter(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == recruiter.id,
        ).first()
        if not membership:
            membership = OrganizationMembership(
                organization_id=org.id,
                user_id=recruiter.id,
                role="recruiter",
            )
            db.add(membership)

        # 4. Jobs with realistic JDs
        jobs_data = [
            {
                "title": "Senior Python & AI Engineer",
                "location": "Remote / Hybrid",
                "description": (
                    "We are seeking a Senior Python & AI Engineer to lead the design and implementation "
                    "of intelligent backend services and machine learning integrations. You will architect "
                    "high-performance RESTful APIs with FastAPI, integrate models from Hugging Face and PyTorch, "
                    "build semantic vector search retrieval pipelines, and containerize microservices using Docker. "
                    "Required qualifications: Deep proficiency in Python and FastAPI. Experience with Machine Learning, "
                    "Hugging Face models, Docker, and PostgreSQL. Preferred qualifications: Hands-on experience with "
                    "PyTorch, LangChain, Redis caching, and vector databases."
                ),
8552
                        {
                            "key": s.lower().replace(" ", "-"),
                            "requirement_type": "preferred",
                            "description": f"Experience with {s}",
                            "evidence": [],
                        }
                        for s in job_info["preferred_skills"]
                    ],
                    "experience_requirements": [
                        {
                            "key": "senior-experience",
                            "requirement_type": "required",
                            "description": "4+ years of relevant industry experience",
                            "evidence": [],
                        }
                    ],
                    "education_requirements": [],
                    "responsibilities": ["Design, build, and maintain production systems."],
                    "unknown_fields": [],
                }

                job_version = JobVersion(
                    job_id=new_job.id,
                    version_number=1,
                    description=job_info["description"],
                    status="approved",
                    analysis_json=analysis,
                    approved_at=utc_now(),
                )
                db.add(job_version)
                db.flush()

                for req in analysis["required_skills"]:
                    db.add(
                        JobRequirement(
                            job_version_id=job_version.id,
                            requirement_key=f"required:{req['key']}",
                            requirement_type="required",
                            description=req["description"],
                            evidence=req["evidence"],
                        )
                    )
                for req in analysis["preferred_skills"]:
                    db.add(
                        JobRequirement(
                            job_version_id=job_version.id,
                            requirement_key=f"preferred:{req['key']}",
                            requirement_type="preferred",
                            description=req["description"],
                            evidence=req["evidence"],
                        )
                    )
                print(f"Created job opening: {new_job.title}")

        # 5. Candidates with detailed extracted resumes
        candidates_data = [
            {
                "email": "amara.johnson@example.com",
                "name": "Amara Johnson",
                "headline": "Senior Python & AI Engineer · 7 yrs exp",
                "location": "New York, NY",
                "skills": ["Python", "FastAPI", "Hugging Face", "Machine Learning", "PyTorch", "Docker", "PostgreSQL", "LangChain"],
                "work_history": [
                    {
                        "employer": "ScaleTech Systems",
                        "title": "Staff AI Engineer",
                        "start_date": "2022",
                        "end_date": "Present",
                        "description": "Architected distributed FastAPI backend services handling 15M requests/day and integrated Hugging Face models for real-time document extraction and RAG pipelines.",
                        "evidence": [{"source": "work_history[0]", "text": "Engineered FastAPI services and Hugging Face inference pipeline."}],
                    },
                    {
                        "employer": "DataFlow Labs",
                        "title": "Senior Python Developer",
                        "start_date": "2019",
                        "end_date": "2022",
                        "description": "Built containerized Python microservices on Docker and maintained PostgreSQL database clusters.",
                        "evidence": [{"source": "work_history[1]", "text": "Deployed Docker containers with PostgreSQL and Redis."}],
                    },
                ],
                "projects": [
                    {
                        "name": "Hugging Face Vector Search Engine",
                        "description": "Production semantic search application using sentence-transformers and PyTorch.",
                        "skills": ["Python", "Hugging Face", "PyTorch", "FastAPI"],
                        "evidence": [],
                    }
                ],
                "education": [
                    {"institution": "Columbia University", "qualification": "B.S.", "field": "Computer Science"}
                ],
            },
            {
                "email": "david.chen@example.com",
                "name": "David Chen",
                "headline": "AI & Machine Learning Engineer · 5 yrs exp",
                "location": "San Francisco, CA",
                "skills": ["Python", "Machine Learning", "Hugging Face", "PyTorch", "NLP", "FastAPI", "Docker", "Transformers"],
                "work_history": [
                    {
                        "employer": "DeepScale AI",
                        "title": "Lead ML Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "description": "Fine-tuned open-source Hugging Face LLMs and deployed low-latency inference APIs using FastAPI and PyTorch.",
                        "evidence": [{"source": "work_history[0]", "text": "Fine-tuned Hugging Face transformer models with PyTorch."}],
                    }
                ],
                "projects": [
                    {
                        "name": "FastAPI Model Serving Hub",
                        "description": "Scalable REST API for model serving with Docker.",
                        "skills": ["FastAPI", "Docker", "Python"],
                        "evidence": [],
                    }
                ],
                "education": [
                    {"institution": "UC Berkeley", "qualification": "M.S.", "field": "Artificial Intelligence"}
                ],
            },
            {
                "email": "elena.rostova@example.com",
                "name": "Elena Rostova",
                "headline": "Backend Systems Engineer · 6 yrs exp",
                "location": "Austin, TX",
                "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "REST APIs", "Microservices"],
                "work_history": [
                    {
                        "employer": "CloudCorp",
                        "title": "Senior Backend Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "description": "Built high-concurrency FastAPI microservices backed by PostgreSQL and Redis. Designed automated Docker deployment pipelines.",
                        "evidence": [{"source": "work_history[0]", "text": "Built FastAPI microservices with PostgreSQL."}],
                    }
                ],
                "projects": [
                    {
                        "name": "Distributed Task Scheduler",
                        "description": "Asynchronous job scheduler using Python and Redis.",
                        "skills": ["Python", "FastAPI", "Docker"],
                        "evidence": [],
                    }
                ],
                "education": [
                    {"institution": "UT Austin", "qualification": "B.S.", "field": "Computer Engineering"}
                ],
            },
            {
                "email": "marcus.sterling@example.com",
                "name": "Marcus Sterling",
                "headline": "Full Stack Python / React Developer · 4 yrs exp",
                "location": "Remote",
                "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL", "Docker", "REST APIs"],
                "work_history": [
                    {
                        "employer": "Nexa Digital",
                        "title": "Full Stack Engineer",
                        "start_date": "2022",
                        "end_date": "Present",
                        "description": "Developed full-stack web applications with React, TypeScript frontends and FastAPI Python backends.",
                        "evidence": [{"source": "work_history[0]", "text": "Developed React and FastAPI web applications."}],
                    }
                ],
                "projects": [
                    {
                        "name": "Enterprise Dashboard",
                        "description": "React and TypeScript portal consuming FastAPI endpoints.",
                        "skills": ["React", "FastAPI", "Python"],
                        "evidence": [],
                    }
                ],
                "education": [
                    {"institution": "University of Washington", "qualification": "B.S.", "field": "Informatics"}
                ],
            },
            {
                "email": "priya.sharma@example.com",
                "name": "Priya Sharma",
                "headline": "Data & AI Engineer · 5 yrs exp",
                "location": "Seattle, WA",
                "skills": ["Python", "Machine Learning", "PostgreSQL", "Docker", "FastAPI", "Airflow", "SQL"],
                "work_history": [
                    {
                        "employer": "OmniAnalytics",
                        "title": "Data Platform Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "description": "Engineered automated data pipelines using Python, SQL, and Airflow, deploying FastAPI endpoints for inference scoring.",
                        "evidence": [{"source": "work_history[0]", "text": "Built Python and FastAPI data inference microservices."}],
                    }
                ],
                "projects": [
                    {
                        "name": "Streaming ML Analytics",
                        "description": "Event-driven data processor with Docker and PostgreSQL.",
                        "skills": ["Python", "Docker", "PostgreSQL"],
                        "evidence": [],
                    }
                ],
                "education": [
                    {"institution": "Georgia Tech", "qualification": "M.S.", "field": "Computer Science"}
                ],
            },
            {
                "email": "sophia.vance@example.com",
                "name": "Sophia Vance",
                "headline": "Lead Product Designer · 8 yrs exp",
                "location": "Brooklyn, NY",
                "skills": ["Figma", "Design Systems", "User Research", "Prototyping", "Interaction Design", "Accessibility"],
                "work_history": [
                    {
                        "employer": "Northstar Studios",
                        "title": "Principal Product Designer",
                        "start_date": "2018",
                        "end_date": "Present",
                        "description": "Led complete UI/UX overhaul and unified design system in Figma adopted by 8 product teams.",
                        "evidence": [{"source": "work_history[0]", "text": "Built and governed enterprise design system in Figma."}],
                    }
                ],
                "projects": [
                    {
                        "name": "Enterprise UI Component Library",
                        "description": "Accessible component library in Figma for web and mobile.",
                        "skills": ["Figma", "Design Systems", "User Research"],
                        "evidence": [],
                    }
                ],
                "education": [
                    {"institution": "Rhode Island School of Design", "qualification": "B.F.A.", "field": "Graphic & Interaction Design"}
                ],
            },
            {
                "email": "robert.miller@example.com",
                "name": "Robert Miller",
                "headline": "Senior Financial Controller · 10 yrs exp",
                "location": "Chicago, IL",
                "skills": ["Financial Modeling", "Budgeting", "Excel", "GAAP", "QuickBooks", "Tax Accounting"],
                "work_history": [
                    {
                        "employer": "FinGroup Corporate",
                        "title": "Controller",
                        "start_date": "2016",
                        "end_date": "Present",
                        "description": "Managed corporate financial budgeting, audits, tax accounting, and GAAP compliance for mid-sized enterprise.",
                        "evidence": [],
                    }
                ],
                "projects": [],
                "education": [
                    {"institution": "University of Illinois", "qualification": "B.S.", "field": "Accounting & Finance"}
                ],
            },
        ]

        for cand_info in candidates_data:
            cand = db.query(User).filter(User.email == cand_info["email"]).first()
            if not cand:
                cand = User(
                    email=cand_info["email"],
                    display_name=cand_info["name"],
                    password_hash=hash_password("Password123456!"),
                    role="candidate",
                )
                db.add(cand)
                db.flush()

                db.add(
                    CandidateProfile(
                        user_id=cand.id,
                        headline=cand_info["headline"],
                        location=cand_info["location"],
                    )
                )

                resume = Resume(candidate_id=cand.id)
                db.add(resume)
                db.flush()

                raw_bytes = f"{cand_info['name']}\n{cand_info['headline']}\nSkills: {', '.join(cand_info['skills'])}".encode()
                sha256 = hashlib.sha256(raw_bytes).hexdigest()

                storage_root = get_settings().storage_root.resolve()
                cand_dir = storage_root / cand.id
                cand_dir.mkdir(parents=True, exist_ok=True)
                file_path = cand_dir / f"resume_{cand.id[:8]}.txt"
                file_path.write_bytes(raw_bytes)
                storage_key = f"{cand.id}/resume_{cand.id[:8]}.txt"

                version = ResumeVersion(
                    resume_id=resume.id,
                    version_number=1,
                    original_filename=f"{cand_info['name'].lower().replace(' ', '_')}_resume.pdf",
                    storage_key=storage_key,
                    mime_type="application/pdf",
                    byte_size=len(raw_bytes),
                    source_sha256=sha256,
                    status="complete",
                )
                db.add(version)
                db.flush()

                # Consent
                db.add(ResumeConsent(candidate_id=cand.id, resume_version_id=version.id, scope="ai_processing"))
                db.add(ResumeConsent(candidate_id=cand.id, resume_version_id=version.id, scope="recruiter_search"))

                # Extraction
                extraction_payload = {
                    "schema_version": "resume.v1",
                    "headline": cand_info["headline"],
                    "location": cand_info["location"],
                    "summary": f"{cand_info['name']} is a {cand_info['headline']}.",
                    "skills": [
                        {
                            "name": s,
                            "evidence": [{"source": "skills", "text": f"Proficient in {s}"}],
                        }
                        for s in cand_info["skills"]
                    ],
                    "work_history": cand_info["work_history"],
                    "education": cand_info["education"],
                    "projects": cand_info["projects"],
                    "certifications": [],
                    "languages": ["English"],
                    "unknown_fields": [],
                }

                db.add(
                    ResumeExtraction(
                        resume_version_id=version.id,
                        schema_version="resume.v1",
                        prompt_version="resume-extraction-v1",
                        provider="huggingface",
                        model_id="Qwen/Qwen2.5-72B-Instruct",
                        extraction_json=extraction_payload,
                        review_status="confirmed",
                    )
                )

                # Search index
                search_text = (
                    f"{cand_info['name']} {cand_info['headline']} {cand_info['location']} "
                    f"{' '.join(cand_info['skills'])} "
                    f"{' '.join(wh.get('description', '') for wh in cand_info['work_history'])}"
                )
                upsert_resume_search(
                    db,
                    resume_version_id=version.id,
                    candidate_id=cand.id,
                    searchable_text=search_text,
                )
                print(f"Created candidate: {cand_info['name']} ({cand_info['headline']})")

        db.commit()
    print("Database seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
