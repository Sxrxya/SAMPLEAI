"""Tandem Repeatable Test Dataset Seeder

Seeds:
- 3 Organizations
- 3 Recruiter accounts (independent authentication)
- 6 Job descriptions with reviewed and approved requirements
- 25 Synthetic candidate profiles with realistic resume files, structured extractions,
  and confirmed active recruiter_search consents.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.config import get_settings
from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    CandidateProfile,
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


def reset_database() -> None:
    """Safely wipe database and file storage."""
    storage_root = get_settings().storage_root.resolve()
    if storage_root.exists():
        for item in storage_root.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file() and not item.name.startswith("."):
                item.unlink()

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS resume_search;"))
    initialize_search_index()


def seed_data() -> None:
    print("=== SEEDING TANDEM MULTI-EMPLOYER LOCAL TEST DATASET ===")
    reset_database()
    print("✓ Storage and SQLite schema initialized.")

    with SessionLocal() as db:
        # Platform Admin
        admin = User(
            email="admin@tandem.test",
            display_name="Platform Admin",
            password_hash=hash_password("AdminPassword123!"),
            role="admin",
        )
        db.add(admin)

        # ---------------------------------------------------------------------
        # 3 Organizations and 3 Independent Recruiters
        # ---------------------------------------------------------------------
        orgs_config = [
            {
                "name": "Northstar Labs",
                "recruiter_email": "recruiter.northstar@example.com",
                "recruiter_name": "Marcus Vance",
                "password": "RecruiterPassword123!",
            },
            {
                "name": "Nexus Health Systems",
                "recruiter_email": "recruiter.nexus@example.com",
                "recruiter_name": "Dr. Aris Thorne",
                "password": "RecruiterPassword123!",
            },
            {
                "name": "Horizon Creative Studio",
                "recruiter_email": "recruiter.horizon@example.com",
                "recruiter_name": "Claire Delacroix",
                "password": "RecruiterPassword123!",
            },
        ]

        created_orgs = {}
        created_recruiters = {}

        for oc in orgs_config:
            org = Organization(name=oc["name"], status="verified")
            db.add(org)
            db.flush()
            created_orgs[oc["name"]] = org

            recruiter = User(
                email=oc["recruiter_email"],
                display_name=oc["recruiter_name"],
                password_hash=hash_password(oc["password"]),
                role="recruiter",
            )
            db.add(recruiter)
            db.flush()
            created_recruiters[oc["name"]] = recruiter

            db.add(
                OrganizationMembership(
                    organization_id=org.id,
                    user_id=recruiter.id,
                    role="owner",
                )
            )

        db.flush()
        print("✓ Created 3 independent organizations and recruiter accounts.")

        # ---------------------------------------------------------------------
        # 6 Job Descriptions (2 per organization)
        # ---------------------------------------------------------------------
        jobs_data = [
            # Northstar Labs
            {
                "org": "Northstar Labs",
                "title": "Senior Python & AI Platform Engineer",
                "location": "San Francisco, CA (Remote)",
                "work_arrangement": "remote",
                "min_exp": 36,
                "description": (
                    "Northstar Labs is looking for a Senior Python & AI Platform Engineer to design, deploy, and scale "
                    "our generative AI inference platform. You will build high-concurrency RESTful microservices with FastAPI, "
                    "integrate open-source transformer models from Hugging Face, fine-tune models using PyTorch, and deploy containerized "
                    "services with Docker on PostgreSQL. Required qualifications: Python, FastAPI, Machine Learning, Hugging Face, "
                    "Docker, and PostgreSQL. Preferred qualifications: PyTorch, LangChain, Redis, and Kubernetes."
                ),
                "required": ["Python", "FastAPI", "Machine Learning", "Hugging Face", "Docker", "PostgreSQL"],
                "preferred": ["PyTorch", "LangChain", "Redis", "Kubernetes"],
            },
            {
                "org": "Northstar Labs",
                "title": "Full Stack Web Developer",
                "location": "Austin, TX (Hybrid)",
                "work_arrangement": "hybrid",
                "min_exp": 24,
                "description": (
                    "Join Northstar Labs core engineering team as a Full Stack Web Developer. You will create modern "
                    "user interfaces using React and TypeScript, connect them to high-performance FastAPI backends, and develop "
                    "scalable REST APIs backed by PostgreSQL and Docker. Required qualifications: React, TypeScript, Python, "
                    "FastAPI, and REST APIs. Preferred qualifications: Tailwind CSS, Docker, and PostgreSQL."
                ),
                "required": ["React", "TypeScript", "Python", "FastAPI", "REST APIs"],
                "preferred": ["Tailwind CSS", "Docker", "PostgreSQL"],
            },
            # Nexus Health Systems
            {
                "org": "Nexus Health Systems",
                "title": "Healthcare Data Analyst & SQL Specialist",
                "location": "Boston, MA (On-site)",
                "work_arrangement": "on-site",
                "min_exp": 24,
                "description": (
                    "Nexus Health Systems is seeking a Healthcare Data Analyst to build clinical analytics queries, "
                    "extract clinical metrics from EHR databases, and design automated reporting pipelines. Required qualifications: "
                    "SQL, PostgreSQL, Python, Data Analysis, and Medical Informatics. Preferred qualifications: Microservices, ETL, and Statistics."
                ),
                "required": ["SQL", "PostgreSQL", "Python", "Data Analysis", "Medical Informatics"],
                "preferred": ["Microservices", "ETL", "Statistics"],
            },
            {
                "org": "Nexus Health Systems",
                "title": "Distributed Systems Backend Architect",
                "location": "Boston, MA (Remote)",
                "work_arrangement": "remote",
                "min_exp": 48,
                "description": (
                    "We need an experienced Distributed Systems Backend Architect to scale hospital telemetry microservices. "
                    "You will design fault-tolerant Python services, orchestrate Docker containers with Kubernetes, optimize PostgreSQL "
                    "relational storage, and implement low-latency Redis caching. Required qualifications: Python, Microservices, "
                    "Docker, Kubernetes, PostgreSQL, and Redis. Preferred qualifications: Go, Kafka, and AWS."
                ),
                "required": ["Python", "Microservices", "Docker", "Kubernetes", "PostgreSQL", "Redis"],
                "preferred": ["Go", "Kafka", "AWS"],
            },
            # Horizon Creative Studio
            {
                "org": "Horizon Creative Studio",
                "title": "Senior Product & Design Systems Designer",
                "location": "New York, NY (Hybrid)",
                "work_arrangement": "hybrid",
                "min_exp": 36,
                "description": (
                    "Horizon Creative Studio is hiring a Senior Product Designer to establish our next-generation design system. "
                    "You will lead end-to-end design sprints, conduct user research interviews, build interactive prototypes in Figma, "
                    "and ensure WCAG accessibility standards. Required qualifications: Figma, Design Systems, User Research, "
                    "Prototyping, and Accessibility. Preferred qualifications: UI/UX, Design Strategy, and Wireframing."
                ),
                "required": ["Figma", "Design Systems", "User Research", "Prototyping", "Accessibility"],
                "preferred": ["UI/UX", "Design Strategy", "Wireframing"],
            },
            {
                "org": "Horizon Creative Studio",
                "title": "Front-End UI Engineer",
                "location": "New York, NY (Remote)",
                "work_arrangement": "remote",
                "min_exp": 24,
                "description": (
                    "Horizon is looking for a Front-End UI Engineer to bridge creative design and interactive code. "
                    "You will translate Figma design specifications into accessible React and TypeScript components, using "
                    "Tailwind CSS to implement design tokens. Required qualifications: React, TypeScript, Figma, Tailwind CSS, "
                    "and Accessibility. Preferred qualifications: Design Systems and REST APIs."
                ),
                "required": ["React", "TypeScript", "Figma", "Tailwind CSS", "Accessibility"],
                "preferred": ["Design Systems", "REST APIs"],
            },
        ]

        created_jobs = []
        for jinfo in jobs_data:
            org = created_orgs[jinfo["org"]]
            recruiter = created_recruiters[jinfo["org"]]
            job = Job(
                organization_id=org.id,
                created_by=recruiter.id,
                title=jinfo["title"],
                location=jinfo["location"],
                status="active",
            )
            db.add(job)
            db.flush()

            analysis = {
                "schema_version": "job.v2",
                "role_title": jinfo["title"],
                "location": jinfo["location"],
                "work_arrangement": jinfo["work_arrangement"],
                "min_experience_months": jinfo["min_exp"],
                "max_experience_months": None,
                "required_skills": [
                    {
                        "key": s.lower().replace(" ", "-"),
                        "requirement_type": "required",
                        "description": f"Demonstrated proficiency in {s}",
                        "evidence": [{"source": "job_description", "text": f"Core requirement: {s}"}],
                    }
                    for s in jinfo["required"]
                ],
                "preferred_skills": [
                    {
                        "key": s.lower().replace(" ", "-"),
                        "requirement_type": "preferred",
                        "description": f"Preferred experience with {s}",
                        "evidence": [{"source": "job_description", "text": f"Preferred requirement: {s}"}],
                    }
                    for s in jinfo["preferred"]
                ],
                "experience_requirements": [
                    {
                        "key": "relevant-experience",
                        "requirement_type": "required",
                        "description": f"Minimum {jinfo['min_exp']} months relevant experience",
                        "evidence": [],
                    }
                ],
                "education_requirements": [],
                "certification_requirements": [],
                "project_expectations": [],
                "responsibilities": ["Design and build scalable robust software solutions."],
                "explicit_eligibility_rules": [],
                "unknown_fields": [],
            }

            version = JobVersion(
                job_id=job.id,
                version_number=1,
                description=jinfo["description"],
                status="approved",
                analysis_json=analysis,
                prompt_version="job-v2",
                provider="huggingface",
                model_id="Qwen/Qwen2.5-72B-Instruct",
                approved_at=utc_now(),
            )
            db.add(version)
            db.flush()

            for req in analysis["required_skills"]:
                db.add(
                    JobRequirement(
                        job_version_id=version.id,
                        requirement_key=f"required:{req['key']}",
                        requirement_type="required",
                        description=req["description"],
                        evidence=req["evidence"],
                    )
                )
            for req in analysis["preferred_skills"]:
                db.add(
                    JobRequirement(
                        job_version_id=version.id,
                        requirement_key=f"preferred:{req['key']}",
                        requirement_type="preferred",
                        description=req["description"],
                        evidence=req["evidence"],
                    )
                )

            created_jobs.append(job)

        db.flush()
        print(f"✓ Created 6 confirmed and approved job descriptions across 3 organizations.")

        # ---------------------------------------------------------------------
        # 25 Synthetic Candidates
        # ---------------------------------------------------------------------
        candidates_seed = [
            # 1. Amara Johnson - Top AI/Platform Engineer
            {
                "email": "amara.johnson@example.com",
                "name": "Amara Johnson",
                "headline": "Senior AI & Platform Engineer · 6 yrs exp",
                "location": "San Francisco, CA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Built high-throughput model serving pipelines in Python 3.12"),
                    ("FastAPI", "DEMONSTRATED", "Designed REST APIs serving 15M daily requests on FastAPI"),
                    ("Machine Learning", "DEMONSTRATED", "Trained and deployed transformer models in production"),
                    ("Hugging Face", "DEMONSTRATED", "Integrated Qwen and Llama-3 models from Hugging Face hub"),
                    ("Docker", "DEMONSTRATED", "Maintained multi-stage Docker build containers"),
                    ("PostgreSQL", "DEMONSTRATED", "Engineered relational schema with partitioning in PostgreSQL"),
                    ("PyTorch", "CONTEXTUAL", "Implemented PyTorch inference pipelines"),
                    ("Redis", "CONTEXTUAL", "Implemented distributed caching with Redis"),
                ],
                "work_history": [
                    {
                        "employer": "Cortex Labs",
                        "title": "Senior AI Platform Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Architected low-latency inference microservices using Python, FastAPI, Hugging Face models, and PostgreSQL.",
                    },
                    {
                        "employer": "DataFlow Systems",
                        "title": "Backend Software Engineer",
                        "start_date": "2018",
                        "end_date": "2020",
                        "duration_months": 24,
                        "description": "Developed backend APIs in Python and containerized services using Docker.",
                    },
                ],
                "projects": [
                    {
                        "name": "Distributed LLM Serving Engine",
                        "description": "Engineered a low-latency model inference gateway in Python and FastAPI with Hugging Face transformers.",
                        "skills": ["Python", "FastAPI", "Hugging Face", "Docker"],
                    }
                ],
                "education": [{"institution": "Columbia University", "qualification": "B.S.", "field": "Computer Science"}],
                "certifications": ["AWS Certified Solutions Architect"],
                "achievements": ["Speaker at PyCon 2023 on High-Performance FastAPI"],
            },
            # 2. David Chen - Lead ML & NLP Engineer
            {
                "email": "david.chen@example.com",
                "name": "David Chen",
                "headline": "Lead ML & NLP Engineer · 5 yrs exp",
                "location": "San Francisco, CA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Authored production ML pipelines in Python"),
                    ("Machine Learning", "DEMONSTRATED", "Fine-tuned deep learning models on large datasets"),
                    ("Hugging Face", "DEMONSTRATED", "Deployed models with Hugging Face text generation inference"),
                    ("PyTorch", "DEMONSTRATED", "Trained custom neural networks with PyTorch"),
                    ("NLP", "DEMONSTRATED", "Implemented tokenization and embedding models"),
                    ("FastAPI", "CONTEXTUAL", "Exposed model endpoints using FastAPI"),
                    ("Docker", "CONTEXTUAL", "Dockerized inference containers"),
                    ("PostgreSQL", "CONTEXTUAL", "Stored feature store metadata in PostgreSQL"),
                ],
                "work_history": [
                    {
                        "employer": "DeepScale AI",
                        "title": "Lead ML Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Fine-tuned Hugging Face transformer models with PyTorch and served APIs with FastAPI.",
                    },
                    {
                        "employer": "LanguageTech",
                        "title": "Machine Learning Engineer",
                        "start_date": "2019",
                        "end_date": "2021",
                        "duration_months": 24,
                        "description": "Engineered NLP text classification pipelines in Python and Docker.",
                    },
                ],
                "projects": [
                    {
                        "name": "Neural Semantic Search Engine",
                        "description": "Semantic retrieval system using Hugging Face embeddings and Python.",
                        "skills": ["Python", "Machine Learning", "Hugging Face"],
                    }
                ],
                "education": [{"institution": "UC Berkeley", "qualification": "M.S.", "field": "Artificial Intelligence"}],
                "certifications": [],
                "achievements": ["Co-authored paper on Efficient Transformer Quantization"],
            },
            # 3. Priya Sharma - Full Stack Python/React Specialist
            {
                "email": "priya.sharma@example.com",
                "name": "Priya Sharma",
                "headline": "Full Stack Engineer (React & FastAPI) · 4 yrs exp",
                "location": "Seattle, WA",
                "skills": [
                    ("React", "DEMONSTRATED", "Built high-performance single page applications in React 18"),
                    ("TypeScript", "DEMONSTRATED", "Maintained strict TypeScript types across 40k LOC frontend"),
                    ("Python", "DEMONSTRATED", "Developed REST APIs using Python and FastAPI"),
                    ("FastAPI", "DEMONSTRATED", "Built OpenAPI validated microservices with FastAPI"),
                    ("REST APIs", "DEMONSTRATED", "Architected idempotent REST endpoints"),
                    ("PostgreSQL", "DEMONSTRATED", "Designed normalized relational databases in PostgreSQL"),
                    ("Docker", "CONTEXTUAL", "Containerized local dev environment with Docker"),
                    ("Tailwind CSS", "CONTEXTUAL", "Styled components with Tailwind CSS"),
                ],
                "work_history": [
                    {
                        "employer": "OmniStack Solutions",
                        "title": "Full Stack Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Engineered React and TypeScript frontends backed by Python FastAPI services.",
                    }
                ],
                "projects": [
                    {
                        "name": "Interactive Analytics Dashboard",
                        "description": "Responsive dashboard using React, TypeScript, and FastAPI with REST APIs.",
                        "skills": ["React", "TypeScript", "FastAPI", "Python"],
                    }
                ],
                "education": [{"institution": "University of Washington", "qualification": "B.S.", "field": "Computer Science"}],
                "certifications": [],
                "achievements": [],
            },
            # 4. Elena Rostova - Senior Backend Systems Engineer
            {
                "email": "elena.rostova@example.com",
                "name": "Elena Rostova",
                "headline": "Senior Backend Systems Engineer · 6 yrs exp",
                "location": "Austin, TX",
                "skills": [
                    ("Python", "DEMONSTRATED", "Wrote scalable async backend engines in Python"),
                    ("FastAPI", "DEMONSTRATED", "Deployed production FastAPI microservices"),
                    ("PostgreSQL", "DEMONSTRATED", "Tuned query plans and managed indexes in PostgreSQL"),
                    ("Docker", "DEMONSTRATED", "Orchestrated multi-service environments with Docker"),
                    ("Redis", "DEMONSTRATED", "Implemented pub/sub and distributed locking with Redis"),
                    ("Microservices", "DEMONSTRATED", "Decomposed monolithic systems into microservices"),
                    ("Kubernetes", "DEMONSTRATED", "Deployed Helm charts to production Kubernetes clusters"),
                ],
                "work_history": [
                    {
                        "employer": "CloudCorp Systems",
                        "title": "Senior Backend Engineer",
                        "start_date": "2019",
                        "end_date": "Present",
                        "duration_months": 60,
                        "description": "Architected resilient microservices with Python, FastAPI, Docker, Kubernetes, and PostgreSQL.",
                    }
                ],
                "projects": [
                    {
                        "name": "High-Throughput Task Broker",
                        "description": "Distributed task queue in Python using Redis and Docker.",
                        "skills": ["Python", "FastAPI", "Redis", "Docker"],
                    }
                ],
                "education": [{"institution": "UT Austin", "qualification": "B.S.", "field": "Computer Engineering"}],
                "certifications": ["CKA Certified Kubernetes Administrator"],
                "achievements": [],
            },
            # 5. Marcus Sterling - AI Research & Inference Engineer
            {
                "email": "marcus.sterling@example.com",
                "name": "Marcus Sterling",
                "headline": "AI & Inference Engineer · 3 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Core development in Python"),
                    ("PyTorch", "DEMONSTRATED", "Fine-tuned models with PyTorch"),
                    ("Hugging Face", "DEMONSTRATED", "Deployed models with Hugging Face pipelines"),
                    ("Machine Learning", "DEMONSTRATED", "Implemented supervised and unsupervised ML"),
                    ("FastAPI", "CONTEXTUAL", "Served model outputs over FastAPI"),
                    ("Docker", "CONTEXTUAL", "Packaged models into Docker images"),
                    ("PostgreSQL", "CONTEXTUAL", "Stored experiment results in PostgreSQL"),
                ],
                "work_history": [
                    {
                        "employer": "VectorAI Dynamics",
                        "title": "AI Software Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Trained machine learning models and built deployment services in Python and FastAPI.",
                    }
                ],
                "projects": [
                    {
                        "name": "Hugging Face Inference Optimizer",
                        "description": "Benchmarking low-latency PyTorch model execution in Docker.",
                        "skills": ["Python", "Hugging Face", "PyTorch", "Docker"],
                    }
                ],
                "education": [{"institution": "Harvard University", "qualification": "M.S.", "field": "Data Science"}],
                "certifications": [],
                "achievements": [],
            },
            # 6. Sophia Vance - Principal Product Designer
            {
                "email": "sophia.vance@example.com",
                "name": "Sophia Vance",
                "headline": "Principal Product Designer · 7 yrs exp",
                "location": "New York, NY",
                "skills": [
                    ("Figma", "DEMONSTRATED", "Created multi-tier component libraries and tokens in Figma"),
                    ("Design Systems", "DEMONSTRATED", "Engineered design system adopted across 8 product teams"),
                    ("User Research", "DEMONSTRATED", "Conducted 60+ qualitative user research sessions"),
                    ("Prototyping", "DEMONSTRATED", "Built high-fidelity interactive prototypes in Figma"),
                    ("Accessibility", "DEMONSTRATED", "Audited and implemented WCAG 2.1 AA compliant UI systems"),
                    ("UI/UX", "DEMONSTRATED", "Complete end-to-end UI/UX product design lifecycle"),
                ],
                "work_history": [
                    {
                        "employer": "Fieldwork Design Group",
                        "title": "Lead Product Designer",
                        "start_date": "2018",
                        "end_date": "Present",
                        "duration_months": 72,
                        "description": "Led design systems, user research interviews, and accessible Figma prototypes.",
                    }
                ],
                "projects": [
                    {
                        "name": "Global Accessible Design System",
                        "description": "Comprehensive Figma component library meeting WCAG accessibility guidelines.",
                        "skills": ["Figma", "Design Systems", "Accessibility", "Prototyping"],
                    }
                ],
                "education": [{"institution": "Rhode Island School of Design", "qualification": "B.F.A.", "field": "Graphic Design"}],
                "certifications": ["CPACC Certified Professional in Accessibility Core Competencies"],
                "achievements": ["Design System Award 2022 Winner"],
            },
            # 7. Liam O'Connor - UI/UX & Interaction Designer
            {
                "email": "liam.oconnor@example.com",
                "name": "Liam O'Connor",
                "headline": "Senior Interaction Designer · 4 yrs exp",
                "location": "New York, NY",
                "skills": [
                    ("Figma", "DEMONSTRATED", "Expert level Figma component architecture and variables"),
                    ("Design Systems", "DEMONSTRATED", "Created design system documentation and tokens"),
                    ("Prototyping", "DEMONSTRATED", "Advanced interactive state prototypes in Figma"),
                    ("User Research", "CONTEXTUAL", "Conducted usability testing interviews"),
                    ("Accessibility", "CONTEXTUAL", "Designed accessible color contrast patterns"),
                    ("UI/UX", "DEMONSTRATED", "B2B SaaS product design and interaction workflows"),
                ],
                "work_history": [
                    {
                        "employer": "Elevate Studio",
                        "title": "Senior UX Designer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Designed product interfaces in Figma, built prototypes, and maintained component libraries.",
                    }
                ],
                "projects": [
                    {
                        "name": "SaaS Design System 2.0",
                        "description": "Figma interactive design system and responsive prototypes.",
                        "skills": ["Figma", "Design Systems", "Prototyping"],
                    }
                ],
                "education": [{"institution": "Pratt Institute", "qualification": "B.S.", "field": "Industrial Design"}],
                "certifications": [],
                "achievements": [],
            },
            # 8. Maya Lin - Frontend UI & Design System Engineer
            {
                "email": "maya.lin@example.com",
                "name": "Maya Lin",
                "headline": "Front-End UI Engineer (React/TypeScript/Figma) · 3 yrs exp",
                "location": "New York, NY",
                "skills": [
                    ("React", "DEMONSTRATED", "Created accessible design token components in React"),
                    ("TypeScript", "DEMONSTRATED", "Authored strongly typed reusable UI component libraries"),
                    ("Figma", "DEMONSTRATED", "Translated Figma tokens directly into React CSS modules"),
                    ("Tailwind CSS", "DEMONSTRATED", "Implemented utility styling with Tailwind CSS"),
                    ("Accessibility", "DEMONSTRATED", "Implemented keyboard navigation and ARIA attributes"),
                    ("Design Systems", "CONTEXTUAL", "Co-maintained company web design system"),
                ],
                "work_history": [
                    {
                        "employer": "Kite Creative Tech",
                        "title": "UI Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Implemented accessible React and TypeScript UI components matching Figma design specs.",
                    }
                ],
                "projects": [
                    {
                        "name": "Accessible Component Library",
                        "description": "React and TypeScript component library with Tailwind CSS and full WCAG compliance.",
                        "skills": ["React", "TypeScript", "Tailwind CSS", "Accessibility"],
                    }
                ],
                "education": [{"institution": "NYU", "qualification": "B.S.", "field": "Digital Media"}],
                "certifications": [],
                "achievements": [],
            },
            # 9. Kavita Patel - Healthcare Data Analyst & SQL Specialist
            {
                "email": "kavita.patel@example.com",
                "name": "Kavita Patel",
                "headline": "Clinical Data Analyst & SQL Specialist · 4 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("SQL", "DEMONSTRATED", "Authored advanced analytical SQL queries with CTEs and window functions"),
                    ("PostgreSQL", "DEMONSTRATED", "Administered clinical PostgreSQL data warehouse"),
                    ("Python", "DEMONSTRATED", "Automated data ETL scripts using Python and pandas"),
                    ("Data Analysis", "DEMONSTRATED", "Performed clinical outcome cohort analysis"),
                    ("Medical Informatics", "DEMONSTRATED", "Processed HL7/FHIR health records"),
                    ("ETL", "CONTEXTUAL", "Designed automated batch ETL pipelines"),
                ],
                "work_history": [
                    {
                        "employer": "Metropolitan Health Analytics",
                        "title": "Clinical Data Analyst",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Extracted and analyzed clinical metrics in PostgreSQL and Python using SQL and medical informatics.",
                    }
                ],
                "projects": [
                    {
                        "name": "Clinical Patient Cohort Pipeline",
                        "description": "SQL and Python reporting engine analyzing patient records in PostgreSQL.",
                        "skills": ["SQL", "PostgreSQL", "Python", "Data Analysis"],
                    }
                ],
                "education": [{"institution": "Boston University", "qualification": "B.S.", "field": "Health Informatics"}],
                "certifications": [],
                "achievements": [],
            },
            # 10. James Wilson - Clinical Data Scientist
            {
                "email": "james.wilson@example.com",
                "name": "James Wilson",
                "headline": "Healthcare Data Scientist · 3 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Data science modeling in Python"),
                    ("SQL", "DEMONSTRATED", "Complex data extraction in SQL"),
                    ("PostgreSQL", "DEMONSTRATED", "Query optimization on PostgreSQL healthcare schemas"),
                    ("Data Analysis", "DEMONSTRATED", "Statistical analysis on clinical trials"),
                    ("Medical Informatics", "DEMONSTRATED", "Validated clinical coding and ICD-10 data"),
                    ("Statistics", "CONTEXTUAL", "Conducted parametric and non-parametric hypothesis testing"),
                ],
                "work_history": [
                    {
                        "employer": "BioHealth Partners",
                        "title": "Data Scientist",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Analyzed patient outcomes using SQL, Python, and PostgreSQL in a medical informatics environment.",
                    }
                ],
                "projects": [
                    {
                        "name": "EHR Predictive Analytics",
                        "description": "Statistical modeling on healthcare records with Python and PostgreSQL.",
                        "skills": ["Python", "SQL", "PostgreSQL", "Data Analysis"],
                    }
                ],
                "education": [{"institution": "Tufts University", "qualification": "M.S.", "field": "Biostatistics"}],
                "certifications": [],
                "achievements": [],
            },
            # 11. Tariq Al-Mansoor - Distributed Cloud Architect
            {
                "email": "tariq.mansoor@example.com",
                "name": "Tariq Al-Mansoor",
                "headline": "Distributed Systems Architect · 7 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Engineered asynchronous distributed backends in Python"),
                    ("Microservices", "DEMONSTRATED", "Architected 20+ decoupled microservices"),
                    ("Docker", "DEMONSTRATED", "Built secure containerized workloads with Docker"),
                    ("Kubernetes", "DEMONSTRATED", "Production multi-cluster Kubernetes operator management"),
                    ("PostgreSQL", "DEMONSTRATED", "High-availability PostgreSQL with replication"),
                    ("Redis", "DEMONSTRATED", "Distributed in-memory caching and Redis queues"),
                    ("AWS", "CONTEXTUAL", "Cloud infrastructure deployment on AWS"),
                    ("Go", "CONTEXTUAL", "High-concurrency microservices in Go"),
                ],
                "work_history": [
                    {
                        "employer": "ScaleGrid Infrastructure",
                        "title": "Principal Backend Architect",
                        "start_date": "2017",
                        "end_date": "Present",
                        "duration_months": 84,
                        "description": "Architected distributed microservices with Python, Docker, Kubernetes, PostgreSQL, and Redis.",
                    }
                ],
                "projects": [
                    {
                        "name": "Zero-Downtime Microservice Mesh",
                        "description": "Kubernetes and Docker architecture connecting Python microservices with Redis and PostgreSQL.",
                        "skills": ["Python", "Microservices", "Docker", "Kubernetes", "PostgreSQL", "Redis"],
                    }
                ],
                "education": [{"institution": "MIT", "qualification": "M.S.", "field": "Computer Science"}],
                "certifications": ["AWS Certified Solutions Architect Professional", "CKA Kubernetes"],
                "achievements": ["Patented distributed consensus protocol"],
            },
            # 12. Zoe Martinez - Senior Infrastructure & Backend Engineer
            {
                "email": "zoe.martinez@example.com",
                "name": "Zoe Martinez",
                "headline": "Senior Backend & Kubernetes Engineer · 5 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Backend services in Python"),
                    ("Microservices", "DEMONSTRATED", "Built microservices for event-driven systems"),
                    ("Docker", "DEMONSTRATED", "Container orchestration with Docker"),
                    ("Kubernetes", "DEMONSTRATED", "Kubernetes cluster administration and ingress routing"),
                    ("PostgreSQL", "DEMONSTRATED", "PostgreSQL database performance tuning"),
                    ("Redis", "DEMONSTRATED", "Redis caching and stream processing"),
                ],
                "work_history": [
                    {
                        "employer": "Apex Cloud Systems",
                        "title": "Senior Infrastructure Engineer",
                        "start_date": "2019",
                        "end_date": "Present",
                        "duration_months": 60,
                        "description": "Designed Python backend microservices on Docker and Kubernetes with PostgreSQL and Redis.",
                    }
                ],
                "projects": [
                    {
                        "name": "Cloud Observability Platform",
                        "description": "Microservices metrics aggregation using Python and Redis on Kubernetes.",
                        "skills": ["Python", "Kubernetes", "Docker", "Redis"],
                    }
                ],
                "education": [{"institution": "Northeastern University", "qualification": "B.S.", "field": "Computer Engineering"}],
                "certifications": ["CKA Certified Kubernetes Administrator"],
                "achievements": [],
            },
            # 13. Alexandre Dubois - Full Stack React/Python Developer
            {
                "email": "alexandre.dubois@example.com",
                "name": "Alexandre Dubois",
                "headline": "Full Stack Developer (React / FastAPI) · 3 yrs exp",
                "location": "Austin, TX",
                "skills": [
                    ("React", "DEMONSTRATED", "Frontend application architecture in React"),
                    ("TypeScript", "DEMONSTRATED", "Full stack TypeScript and React components"),
                    ("Python", "DEMONSTRATED", "Backend development in Python"),
                    ("FastAPI", "DEMONSTRATED", "FastAPI endpoint development"),
                    ("REST APIs", "DEMONSTRATED", "Designed RESTful APIs"),
                    ("Tailwind CSS", "CONTEXTUAL", "Component styling with Tailwind CSS"),
                    ("PostgreSQL", "CONTEXTUAL", "Database queries in PostgreSQL"),
                    ("Docker", "CONTEXTUAL", "Docker containerization"),
                ],
                "work_history": [
                    {
                        "employer": "Volt Software",
                        "title": "Full Stack Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Developed React and TypeScript user interfaces connected to FastAPI REST APIs.",
                    }
                ],
                "projects": [
                    {
                        "name": "Customer Portal App",
                        "description": "Full stack application in React, TypeScript, and FastAPI with REST APIs.",
                        "skills": ["React", "TypeScript", "Python", "FastAPI", "REST APIs"],
                    }
                ],
                "education": [{"institution": "UT Dallas", "qualification": "B.S.", "field": "Software Engineering"}],
                "certifications": [],
                "achievements": [],
            },
            # 14. Chloe Bennett - Junior Full Stack Developer (Fresher)
            {
                "email": "chloe.bennett@example.com",
                "name": "Chloe Bennett",
                "headline": "Junior Full Stack Developer · 1 yr exp",
                "location": "Austin, TX",
                "skills": [
                    ("React", "CONTEXTUAL", "Built junior components in React"),
                    ("TypeScript", "CONTEXTUAL", "Basic TypeScript types"),
                    ("Python", "CONTEXTUAL", "Simple Python backend scripts"),
                    ("FastAPI", "CLAIMED", "Learned FastAPI in bootcamp"),
                    ("REST APIs", "CONTEXTUAL", "Consumed REST APIs in frontend"),
                ],
                "work_history": [
                    {
                        "employer": "StartupLab",
                        "title": "Junior Developer",
                        "start_date": "2023",
                        "end_date": "Present",
                        "duration_months": 12,
                        "description": "Contributed to React components and assisted with Python backend routes.",
                    }
                ],
                "projects": [
                    {
                        "name": "Personal Portfolio & Blog",
                        "description": "Web app built using React and TypeScript.",
                        "skills": ["React", "TypeScript"],
                    }
                ],
                "education": [{"institution": "Texas A&M", "qualification": "B.S.", "field": "Information Technology"}],
                "certifications": [],
                "achievements": [],
            },
            # 15. Daniel Kim - ML Graduate (Fresher, Strong Academic Evidence)
            {
                "email": "daniel.kim@example.com",
                "name": "Daniel Kim",
                "headline": "AI & ML Graduate · Academic Research",
                "location": "San Francisco, CA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Extensive academic coding in Python"),
                    ("Machine Learning", "DEMONSTRATED", "Graduate coursework and thesis on Machine Learning"),
                    ("PyTorch", "DEMONSTRATED", "Implemented neural network training loops in PyTorch"),
                    ("Hugging Face", "CONTEXTUAL", "Used Hugging Face transformers for thesis"),
                    ("FastAPI", "CLAIMED", "Built simple model demo with FastAPI"),
                    ("Docker", "CLAIMED", "Basic container usage"),
                ],
                "work_history": [],
                "internships": [
                    {
                        "organization": "National AI Research Center",
                        "role": "Research Intern",
                        "start_date": "2023",
                        "end_date": "2023",
                        "duration_months": 6,
                        "description": "Researched transformer models in Python and PyTorch.",
                    }
                ],
                "projects": [
                    {
                        "name": "Master's Thesis: Efficient Transformer Training",
                        "description": "Benchmarking deep learning architectures with Python, PyTorch, and Hugging Face.",
                        "skills": ["Python", "Machine Learning", "PyTorch", "Hugging Face"],
                    }
                ],
                "education": [{"institution": "Stanford University", "qualification": "M.S.", "field": "Computer Science"}],
                "certifications": [],
                "achievements": ["Graduate Fellowship Award 2023"],
            },
            # 16. Hannah Abbott - Junior Frontend Developer
            {
                "email": "hannah.abbott@example.com",
                "name": "Hannah Abbott",
                "headline": "Junior Frontend Developer · 1 yr exp",
                "location": "New York, NY",
                "skills": [
                    ("React", "DEMONSTRATED", "Built interactive UI views in React"),
                    ("TypeScript", "CONTEXTUAL", "Wrote typed interfaces in TypeScript"),
                    ("Figma", "CONTEXTUAL", "Inspected Figma design handoffs"),
                    ("Tailwind CSS", "DEMONSTRATED", "Designed pages with Tailwind CSS"),
                    ("Accessibility", "CLAIMED", "Basic WCAG awareness"),
                ],
                "work_history": [
                    {
                        "employer": "PixelCrafters",
                        "title": "Junior UI Developer",
                        "start_date": "2023",
                        "end_date": "Present",
                        "duration_months": 12,
                        "description": "Implemented React web components and styled them with Tailwind CSS based on Figma designs.",
                    }
                ],
                "projects": [
                    {
                        "name": "Design Token Showcase",
                        "description": "React component collection styled with Tailwind CSS.",
                        "skills": ["React", "Tailwind CSS"],
                    }
                ],
                "education": [{"institution": "Fordham University", "qualification": "B.A.", "field": "Communications & Web Design"}],
                "certifications": [],
                "achievements": [],
            },
            # 17. Benjamin Hayes - Senior Product Designer
            {
                "email": "benjamin.hayes@example.com",
                "name": "Benjamin Hayes",
                "headline": "Senior Product & Design Systems Designer · 5 yrs exp",
                "location": "New York, NY",
                "skills": [
                    ("Figma", "DEMONSTRATED", "Designed unified component system in Figma"),
                    ("Design Systems", "DEMONSTRATED", "Built and governed enterprise design system"),
                    ("User Research", "DEMONSTRATED", "Conducted generative user research studies"),
                    ("Prototyping", "DEMONSTRATED", "High-fidelity motion and micro-interaction prototyping"),
                    ("Accessibility", "DEMONSTRATED", "Led accessibility compliance initiative"),
                    ("UI/UX", "DEMONSTRATED", "End-to-end design lifecycle"),
                ],
                "work_history": [
                    {
                        "employer": "ModernUI Labs",
                        "title": "Senior Product Designer",
                        "start_date": "2019",
                        "end_date": "Present",
                        "duration_months": 60,
                        "description": "Created scalable design systems in Figma, led user research sessions, and developed prototypes.",
                    }
                ],
                "projects": [
                    {
                        "name": "Multi-Brand Design System",
                        "description": "Comprehensive design system across web and mobile using Figma and WCAG guidelines.",
                        "skills": ["Figma", "Design Systems", "User Research", "Accessibility"],
                    }
                ],
                "education": [{"institution": "Carnegie Mellon University", "qualification": "B.S.", "field": "Human-Computer Interaction"}],
                "certifications": [],
                "achievements": [],
            },
            # 18. Aisha Bello - Data & Database Engineer
            {
                "email": "aisha.bello@example.com",
                "name": "Aisha Bello",
                "headline": "Database & Data Engineer · 3 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("SQL", "DEMONSTRATED", "Complex SQL query tuning and stored procedures"),
                    ("PostgreSQL", "DEMONSTRATED", "PostgreSQL database administration and schema migrations"),
                    ("Python", "DEMONSTRATED", "Automated ETL pipelines in Python"),
                    ("Data Analysis", "CONTEXTUAL", "Analyzed operational data sets"),
                    ("ETL", "DEMONSTRATED", "Engineered nightly data syncs"),
                    ("Redis", "CONTEXTUAL", "Configured Redis cache layers"),
                ],
                "work_history": [
                    {
                        "employer": "DataSphere Analytics",
                        "title": "Data Engineer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Designed relational database architectures in PostgreSQL and automated data workflows with Python and SQL.",
                    }
                ],
                "projects": [
                    {
                        "name": "PostgreSQL Data Pipeline",
                        "description": "Automated data ingestion engine built using Python and PostgreSQL.",
                        "skills": ["SQL", "PostgreSQL", "Python"],
                    }
                ],
                "education": [{"institution": "University of Massachusetts", "qualification": "B.S.", "field": "Computer Science"}],
                "certifications": [],
                "achievements": [],
            },
            # 19. Vikram Malhotra - DevOps & Cloud Infrastructure Engineer
            {
                "email": "vikram.malhotra@example.com",
                "name": "Vikram Malhotra",
                "headline": "DevOps & Cloud Engineer · 4 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("Docker", "DEMONSTRATED", "Built automated Docker build and scan pipelines"),
                    ("Kubernetes", "DEMONSTRATED", "Managed production Kubernetes deployments"),
                    ("Python", "DEMONSTRATED", "Automated infrastructure tooling in Python"),
                    ("Microservices", "CONTEXTUAL", "Maintained CI/CD for microservice fleet"),
                    ("Redis", "CONTEXTUAL", "Monitored Redis clusters"),
                    ("PostgreSQL", "CONTEXTUAL", "Database backup automation in PostgreSQL"),
                    ("AWS", "DEMONSTRATED", "Cloud deployment on AWS"),
                ],
                "work_history": [
                    {
                        "employer": "InfraCore Cloud",
                        "title": "DevOps Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Deployed microservices on Kubernetes using Docker, Python, and AWS.",
                    }
                ],
                "projects": [
                    {
                        "name": "Automated Kubernetes Pipeline",
                        "description": "Zero-downtime deployment pipeline for Docker microservices on Kubernetes.",
                        "skills": ["Docker", "Kubernetes", "Python"],
                    }
                ],
                "education": [{"institution": "Purdue University", "qualification": "B.S.", "field": "Electrical & Computer Engineering"}],
                "certifications": ["AWS Certified DevOps Engineer Professional", "CKA Kubernetes"],
                "achievements": [],
            },
            # 20. Rachel Green - Junior UX Designer
            {
                "email": "rachel.green@example.com",
                "name": "Rachel Green",
                "headline": "Junior UX Designer · 1 yr exp",
                "location": "New York, NY",
                "skills": [
                    ("Figma", "DEMONSTRATED", "Designed wireframes and UI components in Figma"),
                    ("Prototyping", "CONTEXTUAL", "Created click-through prototypes in Figma"),
                    ("UI/UX", "CONTEXTUAL", "App usability analysis"),
                    ("Design Systems", "CLAIMED", "Learned design system principles in courses"),
                    ("User Research", "CLAIMED", "Participated in user testing notes"),
                ],
                "work_history": [
                    {
                        "employer": "Creative Spark Agency",
                        "title": "Junior UX Designer",
                        "start_date": "2023",
                        "end_date": "Present",
                        "duration_months": 12,
                        "description": "Created wireframes and user interaction flows in Figma.",
                    }
                ],
                "projects": [
                    {
                        "name": "E-Commerce App Wireframes",
                        "description": "Figma interactive wireframes for mobile retail application.",
                        "skills": ["Figma", "Prototyping"],
                    }
                ],
                "education": [{"institution": "Syracuse University", "qualification": "B.S.", "field": "Graphic Design"}],
                "certifications": [],
                "achievements": [],
            },
            # 21. Samuel Torres - Web Developer (Skills Claimed with Weak Evidence)
            {
                "email": "samuel.torres@example.com",
                "name": "Samuel Torres",
                "headline": "Web Developer · Generalist · 2 yrs exp",
                "location": "San Francisco, CA",
                "skills": [
                    ("Python", "CLAIMED", "Listed on resume"),
                    ("FastAPI", "CLAIMED", "Listed on resume"),
                    ("Machine Learning", "CLAIMED", "Listed on resume"),
                    ("Docker", "CLAIMED", "Listed on resume"),
                    ("React", "CONTEXTUAL", "Maintained WordPress and simple React landing pages"),
                    ("WordPress", "DEMONSTRATED", "Built marketing websites on WordPress"),
                ],
                "work_history": [
                    {
                        "employer": "Freelance Web Studio",
                        "title": "Web Specialist",
                        "start_date": "2022",
                        "end_date": "Present",
                        "duration_months": 24,
                        "description": "Maintained small business websites using WordPress, HTML, CSS, and basic JavaScript.",
                    }
                ],
                "projects": [
                    {
                        "name": "Agency Landing Pages",
                        "description": "Created marketing web pages using HTML, CSS, and WordPress.",
                        "skills": ["WordPress", "React"],
                    }
                ],
                "education": [{"institution": "San Jose State University", "qualification": "B.A.", "field": "General Studies"}],
                "certifications": [],
                "achievements": [],
            },
            # 22. Nadia Petrov - Mobile & Embedded Developer (Unrelated projects)
            {
                "email": "nadia.petrov@example.com",
                "name": "Nadia Petrov",
                "headline": "Embedded Systems & Mobile Engineer · 4 yrs exp",
                "location": "Boston, MA",
                "skills": [
                    ("C++", "DEMONSTRATED", "Embedded firmware in C++"),
                    ("Swift", "DEMONSTRATED", "iOS mobile applications in Swift"),
                    ("Kotlin", "DEMONSTRATED", "Android development with Kotlin"),
                    ("Firmware", "DEMONSTRATED", "Microcontroller programming"),
                    ("Python", "CLAIMED", "Basic test scripts in Python"),
                ],
                "work_history": [
                    {
                        "employer": "Embedded Devices Corp",
                        "title": "Embedded Software Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Programmed microcontrollers in C++ and built companion mobile applications in Swift.",
                    }
                ],
                "projects": [
                    {
                        "name": "IoT Sensor Firmware",
                        "description": "Ultra low-power firmware written in C++ for wireless IoT devices.",
                        "skills": ["C++", "Swift"],
                    }
                ],
                "education": [{"institution": "RPI", "qualification": "B.S.", "field": "Electrical Engineering"}],
                "certifications": [],
                "achievements": [],
            },
            # 23. Robert Miller - Corporate Financial Controller (Intentional Non-Match)
            {
                "email": "robert.miller@example.com",
                "name": "Robert Miller",
                "headline": "Corporate Financial Controller · CPA · 8 yrs exp",
                "location": "Chicago, IL",
                "skills": [
                    ("Financial Accounting", "DEMONSTRATED", "Corporate GAAP accounting and reporting"),
                    ("Financial Auditing", "DEMONSTRATED", "Managed external Big 4 annual audits"),
                    ("Tax Compliance", "DEMONSTRATED", "Corporate federal and state tax filings"),
                    ("Corporate Budgeting", "DEMONSTRATED", "Multi-departmental budget forecasting"),
                    ("Excel", "DEMONSTRATED", "Financial modeling with advanced Excel"),
                ],
                "work_history": [
                    {
                        "employer": "FinGroup Corporate Holdings",
                        "title": "Corporate Controller",
                        "start_date": "2016",
                        "end_date": "Present",
                        "duration_months": 96,
                        "description": "Managed corporate financial audits, GAAP compliance, financial modeling, and tax planning.",
                    }
                ],
                "projects": [],
                "education": [{"institution": "University of Illinois", "qualification": "B.S.", "field": "Accounting & Finance"}],
                "certifications": ["Certified Public Accountant (CPA)"],
                "achievements": [],
            },
            # 24. Grace Hopper-Smith - Backend Engineer (Missing Optional Info)
            {
                "email": "grace.hoppersmith@example.com",
                "name": "Grace Hopper-Smith",
                "headline": "Backend Engineer · 3 yrs exp",
                "location": "San Francisco, CA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Developed async backend systems in Python"),
                    ("FastAPI", "DEMONSTRATED", "Built high-throughput APIs with FastAPI"),
                    ("PostgreSQL", "DEMONSTRATED", "Relational database schema modeling in PostgreSQL"),
                    ("Docker", "CONTEXTUAL", "Packaged services with Docker"),
                    ("Machine Learning", "CLAIMED", "Familiar with machine learning concepts"),
                ],
                "work_history": [
                    {
                        "employer": "DataWorks Tech",
                        "title": "Backend Software Developer",
                        "start_date": "2021",
                        "end_date": "Present",
                        "duration_months": 36,
                        "description": "Developed backend REST APIs using Python and FastAPI with PostgreSQL databases.",
                    }
                ],
                "projects": [
                    {
                        "name": "High-Performance REST Gateway",
                        "description": "FastAPI and Python backend system connecting to PostgreSQL.",
                        "skills": ["Python", "FastAPI", "PostgreSQL"],
                    }
                ],
                "education": [],  # Missing optional education info
                "certifications": [],  # Missing optional certifications
                "achievements": [],
            },
            # 25. Kenji Takahashi - AI & Computer Vision Specialist
            {
                "email": "kenji.takahashi@example.com",
                "name": "Kenji Takahashi",
                "headline": "Computer Vision & Deep Learning Engineer · 4 yrs exp",
                "location": "San Francisco, CA",
                "skills": [
                    ("Python", "DEMONSTRATED", "Computer vision model development in Python"),
                    ("PyTorch", "DEMONSTRATED", "Trained convolutional and transformer vision models in PyTorch"),
                    ("Machine Learning", "DEMONSTRATED", "Object detection and image segmentation algorithms"),
                    ("Docker", "DEMONSTRATED", "Deployed GPU accelerated containers with Docker"),
                    ("Hugging Face", "CONTEXTUAL", "Integrated vision transformer models from Hugging Face"),
                    ("FastAPI", "CONTEXTUAL", "Built image inference web endpoints in FastAPI"),
                ],
                "work_history": [
                    {
                        "employer": "VisionAI Technologies",
                        "title": "Computer Vision Engineer",
                        "start_date": "2020",
                        "end_date": "Present",
                        "duration_months": 48,
                        "description": "Developed deep learning vision models in Python and PyTorch and deployed with Docker and FastAPI.",
                    }
                ],
                "projects": [
                    {
                        "name": "Real-time Object Detection Service",
                        "description": "Vision inference engine using PyTorch, Python, and Docker.",
                        "skills": ["Python", "PyTorch", "Machine Learning", "Docker"],
                    }
                ],
                "education": [{"institution": "University of Tokyo", "qualification": "M.S.", "field": "Information Science"}],
                "certifications": [],
                "achievements": ["Published paper at CVPR on Real-time Segmentation"],
            },
        ]

        storage_root = get_settings().storage_root.resolve()
        storage_root.mkdir(parents=True, exist_ok=True)

        for cdata in candidates_seed:
            cand = User(
                email=cdata["email"],
                display_name=cdata["name"],
                password_hash=hash_password("CandidatePassword123!"),
                role="candidate",
            )
            db.add(cand)
            db.flush()

            db.add(
                CandidateProfile(
                    user_id=cand.id,
                    headline=cdata["headline"],
                    location=cdata["location"],
                )
            )

            resume = Resume(candidate_id=cand.id)
            db.add(resume)
            db.flush()

            # Generate realistic synthetic resume text
            skill_lines = ", ".join(s[0] for s in cdata["skills"])
            wh_blocks = []
            for wh in cdata["work_history"]:
                wh_blocks.append(f"{wh['title']} at {wh['employer']} ({wh['start_date']} - {wh['end_date']})\n{wh['description']}")
            wh_text = "\n\n".join(wh_blocks) if wh_blocks else "No commercial work history recorded."

            proj_blocks = []
            for p in cdata["projects"]:
                proj_blocks.append(f"Project: {p['name']}\nSkills: {', '.join(p['skills'])}\n{p['description']}")
            proj_text = "\n\n".join(proj_blocks) if proj_blocks else "No projects recorded."

            resume_content = (
                f"{cdata['name']}\n"
                f"{cdata['headline']} | {cdata['location']}\n"
                f"Contact: {cdata['email']}\n\n"
                f"=== PROFESSIONAL SUMMARY ===\n"
                f"{cdata['name']} is an experienced specialist with a background in: {skill_lines}.\n\n"
                f"=== TECHNICAL SKILLS ===\n"
                f"{skill_lines}\n\n"
                f"=== WORK EXPERIENCE ===\n"
                f"{wh_text}\n\n"
                f"=== PROJECTS ===\n"
                f"{proj_text}\n\n"
                f"=== EDUCATION ===\n"
                f"{', '.join(f'{e['qualification']} in {e['field']} from {e['institution']}' for e in cdata['education']) if cdata['education'] else 'Education details available upon request.'}\n"
            )

            raw_bytes = resume_content.encode("utf-8")
            sha256 = hashlib.sha256(raw_bytes).hexdigest()

            cand_dir = storage_root / cand.id
            cand_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"{cdata['name'].lower().replace(' ', '_').replace('-', '_')}_resume.txt"
            file_path = cand_dir / file_name
            file_path.write_bytes(raw_bytes)
            storage_key = f"{cand.id}/{file_name}"

            version = ResumeVersion(
                resume_id=resume.id,
                version_number=1,
                original_filename=file_name,
                storage_key=storage_key,
                mime_type="text/plain",
                byte_size=len(raw_bytes),
                source_sha256=sha256,
                status="complete",
            )
            db.add(version)
            db.flush()

            # Active consents
            db.add(ResumeConsent(candidate_id=cand.id, resume_version_id=version.id, scope="ai_processing"))
            db.add(ResumeConsent(candidate_id=cand.id, resume_version_id=version.id, scope="recruiter_search"))

            # Structured extraction payload
            structured_skills = [
                {
                    "name": s[0],
                    "category": "technical",
                    "evidence_level": s[1],
                    "evidence": [{"source": "resume_body", "text": s[2]}],
                }
                for s in cdata["skills"]
            ]

            extraction_payload = {
                "schema_version": "resume.v2",
                "contact_info": {
                    "name": cdata["name"],
                    "email": cdata["email"],
                    "location": cdata["location"],
                },
                "headline": cdata["headline"],
                "location": cdata["location"],
                "summary": f"{cdata['name']} is a {cdata['headline']}.",
                "skills": structured_skills,
                "soft_skills": [],
                "work_history": [
                    {
                        "employer": wh["employer"],
                        "title": wh["title"],
                        "start_date": wh["start_date"],
                        "end_date": wh["end_date"],
                        "duration_months": wh.get("duration_months"),
                        "description": wh["description"],
                        "evidence": [{"source": "work_history", "text": wh["description"]}],
                        "status": "EXTRACTED",
                    }
                    for wh in cdata["work_history"]
                ],
                "internships": [
                    {
                        "organization": intern.get("organization"),
                        "role": intern.get("role"),
                        "start_date": intern.get("start_date"),
                        "end_date": intern.get("end_date"),
                        "duration_months": intern.get("duration_months"),
                        "description": intern.get("description"),
                        "skills": [],
                        "evidence": [],
                    }
                    for intern in cdata.get("internships", [])
                ],
                "education": [
                    {
                        "institution": e.get("institution"),
                        "qualification": e.get("qualification"),
                        "field": e.get("field"),
                        "start_date": None,
                        "end_date": None,
                        "evidence": [],
                        "status": "EXTRACTED",
                    }
                    for e in cdata["education"]
                ],
                "projects": [
                    {
                        "name": p["name"],
                        "description": p["description"],
                        "skills": p["skills"],
                        "domain": None,
                        "evidence": [{"source": "projects", "text": p["description"]}],
                        "evidence_level": "DEMONSTRATED",
                    }
                    for p in cdata["projects"]
                ],
                "certifications": [
                    {
                        "name": cert if isinstance(cert, str) else cert.get("name"),
                        "issuer": None,
                        "issue_date": None,
                        "evidence": [],
                    }
                    for cert in cdata["certifications"]
                ],
                "achievements": [
                    {
                        "title": ach,
                        "description": None,
                        "evidence": [],
                    }
                    for ach in cdata["achievements"]
                ],
                "publications": [],
                "languages": ["English"],
                "volunteer_experience": [],
                "unknown_fields": [],
                "field_statuses": {
                    "contact_info": "EXTRACTED",
                    "skills": "EXTRACTED",
                    "work_history": "EXTRACTED" if cdata["work_history"] else "NOT_FOUND",
                    "education": "EXTRACTED" if cdata["education"] else "NOT_FOUND",
                    "projects": "EXTRACTED" if cdata["projects"] else "NOT_FOUND",
                },
                "source_text_summary": resume_content[:2000],
            }

            db.add(
                ResumeExtraction(
                    resume_version_id=version.id,
                    schema_version="resume.v2",
                    prompt_version="resume-v2",
                    provider="huggingface",
                    model_id="Qwen/Qwen2.5-72B-Instruct",
                    extraction_json=extraction_payload,
                    review_status="confirmed",
                )
            )

            # Populate SQLite FTS5 Search Index
            searchable_text = f"{cdata['name']} {skill_lines} {resume_content[:5000]}"
            upsert_resume_search(
                db,
                resume_version_id=version.id,
                candidate_id=cand.id,
                searchable_text=searchable_text,
            )

        db.commit()
        print(f"✓ Created 25 synthetic candidates with confirmed extractions, verified evidence, and search indexes.")
        print("\n=====================================================================")
        print("SEEDING COMPLETE. READY FOR MULTI-EMPLOYER LOCAL TESTING.")
        print("=====================================================================")
        print("Employers available:")
        print("  1. Northstar Labs:           recruiter.northstar@example.com / RecruiterPassword123!")
        print("  2. Nexus Health Systems:     recruiter.nexus@example.com     / RecruiterPassword123!")
        print("  3. Horizon Creative Studio:  recruiter.horizon@example.com   / RecruiterPassword123!")
        print("\nCandidates available (25 total):")
        print("  - amara.johnson@example.com     (Top AI/Platform Engineer)")
        print("  - david.chen@example.com        (Lead ML/NLP Engineer)")
        print("  - priya.sharma@example.com      (Full Stack Python/React)")
        print("  - sophia.vance@example.com      (Principal Product Designer)")
        print("  - kavita.patel@example.com      (Clinical Data Analyst)")
        print("  - tariq.mansoor@example.com     (Distributed Systems Architect)")
        print("  - robert.miller@example.com     (Corporate Controller - Non-Match)")
        print("  ... and 18 additional diverse candidate profiles.")
        print("  All candidate passwords:        CandidatePassword123!")
        print("=====================================================================")


if __name__ == "__main__":
    seed_data()

