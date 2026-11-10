import os
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import User


def main() -> None:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")
    display_name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "Platform admin").strip()
    if not email or len(password) < 12:
        raise SystemExit(
            "Set BOOTSTRAP_ADMIN_EMAIL and a BOOTSTRAP_ADMIN_PASSWORD of at least 12 characters."
        )

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email))
        if existing is not None:
            if existing.role != "admin":
                raise SystemExit("The email belongs to a non-admin account; no role was changed.")
            print("Admin account already exists; no changes made.")
            return
        db.add(
            User(
                email=email,
                display_name=display_name,
                password_hash=hash_password(password),
                role="admin",
            )
        )
        db.commit()
    print("Admin account created. Remove the bootstrap environment variables now.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Bootstrap canceled.")
