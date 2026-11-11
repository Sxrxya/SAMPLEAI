"""Helper tool to bulk-ingest real candidate resumes (PDF, DOCX, TXT) for testing.

Usage:
  python scripts/ingest_real_resumes.py [path_to_resumes_folder]

If no folder is provided, it creates a 'storage/real_resumes' folder where you can drop your resumes.
"""

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import CandidateProfile, Resume, ResumeConsent, ResumeExtraction, ResumeVersion, User
from app.services.documents import extract_text
from app.services.search import upsert_resume_search


def main():
    folder_path = sys.argv[1] if len(sys.argv) > 1 else "storage/real_resumes"
    resumes_dir = Path(folder_path)
    resumes_dir.mkdir(parents=True, exist_ok=True)

    supported_files = [
        f for f in resumes_dir.iterdir()
        if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".txt"]
    ]

    print(f"=== BULK RESUME INGESTION TOOL ===")
    print(f"Scanning directory: {resumes_dir.resolve()}")

    if not supported_files:
        print(f"\nNo resumes found in: {resumes_dir.resolve()}")
        print("Drop your real resume files (.pdf, .docx, or .txt) into that folder and run this script again:")
        print(f"  ..\\.venv\\Scripts\\python.exe scripts/ingest_real_resumes.py {folder_path}")
        return

    print(f"Found {len(supported_files)} resume file(s) to ingest.\n")

    with SessionLocal() as db:
        for idx, file_path in enumerate(supported_files, start=1):
            stem_name = file_path.stem.replace("_", " ").replace("-", " ").title()
            email = f"candidate_{idx}_{file_path.stem.lower()}@example.com"
            raw_bytes = file_path.read_bytes()
            sha256 = hashlib.sha256(raw_bytes).hexdigest()

            # 1. Determine mime type
            ext = file_path.suffix.lower()
            mime_type = (
                "application/pdf" if ext == ".pdf"
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if ext == ".docx"
                else "text/plain"
            )

            # 2. Extract text from document
            try:
                extracted_text = extract_text(raw_bytes, mime_type)
            except Exception as e:
                extracted_text = raw_bytes.decode("utf-8", errors="ignore")

            # 3. Create or get user
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email,
                    display_name=stem_name,
                    password_hash=hash_password("CandidatePassword123!"),
                    role="candidate",
                )
                db.add(user)
                db.flush()

                db.add(CandidateProfile(user_id=user.id, headline=f"{stem_name} · Candidate", location="Remote"))

            # 4. Save resume file to storage
            storage_root = get_settings().storage_root.resolve()
            cand_dir = storage_root / user.id
            cand_dir.mkdir(parents=True, exist_ok=True)
            stored_file = cand_dir / file_path.name
            stored_file.write_bytes(raw_bytes)
            storage_key = f"{user.id}/{file_path.name}"

            # 5. Create Resume & ResumeVersion
            resume = db.query(Resume).filter(Resume.candidate_id == user.id).first()
            if not resume:
                resume = Resume(candidate_id=user.id)
                db.add(resume)
                db.flush()

            version = ResumeVersion(
                resume_id=resume.id,
                version_number=1,
                original_filename=file_path.name,
                storage_key=storage_key,
                mime_type=mime_type,
                byte_size=len(raw_bytes),
                source_sha256=sha256,
                status="complete",
            )
            db.add(version)
            db.flush()

            # 6. Add required consents
            db.add(ResumeConsent(candidate_id=user.id, resume_version_id=version.id, scope="ai_processing"))
            db.add(ResumeConsent(candidate_id=user.id, resume_version_id=version.id, scope="recruiter_search"))

            # 7. Basic extraction payload so candidate is immediately searchable & matchable
            known_skills = [
                "python", "fastapi", "react", "typescript", "figma", "machine learning",
                "hugging face", "pytorch", "docker", "postgresql", "sql", "redis",
                "user research", "design systems", "rest apis", "aws", "kubernetes",
                "airflow", "spark", "nlp", "llm", "transformers", "langchain", "java",
                "c++", "go", "javascript", "html", "css", "node", "express", "graphql"
            ]
            text_lower = extracted_text.lower()
            detected_skills = [s for s in known_skills if s in text_lower]

            extraction_payload = {
                "schema_version": "resume.v1",
                "headline": f"{stem_name} · Professional",
                "location": "Remote",
                "summary": extracted_text[:300].strip(),
                "skills": [
                    {
                        "name": s.title(),
                        "evidence": [{"source": "resume_body", "text": f"Found mention of {s}"}],
                    }
                    for s in detected_skills
                ],
                "work_history": [
                    {
                        "employer": "Previous Company",
                        "title": "Engineer / Specialist",
                        "description": extracted_text[:500].strip(),
                        "evidence": [],
                    }
                ],
                "education": [],
                "projects": [],
                "certifications": [],
                "unknown_fields": [],
            }

            db.add(
                ResumeExtraction(
                    resume_version_id=version.id,
                    schema_version="resume.v1",
                    prompt_version="resume-v1",
                    provider="huggingface",
                    model_id="Qwen/Qwen2.5-72B-Instruct",
                    extraction_json=extraction_payload,
                    review_status="confirmed",
                )
            )

            upsert_resume_search(
                db,
                resume_version_id=version.id,
                candidate_id=user.id,
                searchable_text=f"{stem_name} {' '.join(detected_skills)} {extracted_text[:10000]}",
            )

            print(f"✓ Ingested: {file_path.name} -> {stem_name} (Detected {len(detected_skills)} skills: {', '.join(detected_skills[:5])})")

        db.commit()
        print("\nAll resumes ingested successfully and ready for AI matching!")


if __name__ == "__main__":
    main()

