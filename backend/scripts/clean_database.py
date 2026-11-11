"""Reset database to a clean production-ready state with ZERO mock data.

This removes all demo candidates, resumes, jobs, match runs, and stored files,
and creates 1 verified employer/recruiter account and 1 platform admin account.
"""

import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.config import get_settings
from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Organization, OrganizationMembership, User
from app.services.search import initialize_search_index


def main():
    print("=== TANDEM CLEAN DATABASE RESET ===")
    
    # 1. Clean storage folder
    storage_root = get_settings().storage_root.resolve()
    if storage_root.exists():
        for item in storage_root.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file() and not item.name.startswith("."):
                item.unlink()
        print(f"✓ Storage cleaned at: {storage_root}")

    # 2. Drop and recreate all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 3. Re-initialize FTS5 virtual table
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS resume_search;"))
    initialize_search_index()
    print("✓ Database tables and FTS5 search index recreated from scratch.")

    # 4. Create primary verified recruiter/employer account
    with SessionLocal() as db:
        # Verified Employer Organization
        org = Organization(
            name="My Company",
            status="verified",
        )
        db.add(org)
        db.flush()

        recruiter = User(
            email="recruiter@mycompany.com",
            display_name="Hiring Lead",
            password_hash=hash_password("RecruiterPassword123!"),
            role="recruiter",
        )
        db.add(recruiter)
        db.flush()

        db.add(
            OrganizationMembership(
                organization_id=org.id,
                user_id=recruiter.id,
                role="owner",
            )
        )

        # Platform Admin
        admin = User(
            email="admin@tandem.test",
            display_name="Platform Admin",
            password_hash=hash_password("AdminPassword123!"),
            role="admin",
        )
        db.add(admin)

        db.commit()

        print("\n✓ Clean state initialized with ZERO mock candidates and ZERO mock jobs.")
        print("----------------------------------------------------------------------")
        print("Recruiter Login (to post real JDs and view top 5 matches):")
        print("  Email:    recruiter@mycompany.com")
        print("  Password: RecruiterPassword123!")
        print("  Company:  My Company (Verified)")
        print("\nAdmin Login:")
        print("  Email:    admin@tandem.test")
        print("  Password: AdminPassword123!")
        print("----------------------------------------------------------------------")


if __name__ == "__main__":
    main()

