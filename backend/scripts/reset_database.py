"""Safe reset script for Tandem SQLite database and storage.

Usage:
    python backend/scripts/reset_database.py            # Reset database to empty schema + FTS5 index
    python backend/scripts/reset_database.py --reseed   # Reset and immediately run test seeder
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.config import get_settings
from app.core.db import Base, SessionLocal, engine
from app.services.search import initialize_search_index


def reset_environment():
    print("=== RESETTING TANDEM LOCAL DATABASE & STORAGE ===")

    # 1. Clean storage directory
    storage_root = get_settings().storage_root.resolve()
    if storage_root.exists():
        for item in storage_root.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            elif item.is_file() and not item.name.startswith("."):
                item.unlink()
        print(f"✓ Stored resume artifacts cleaned from {storage_root}")
    else:
        storage_root.mkdir(parents=True, exist_ok=True)
        print(f"✓ Storage directory created at {storage_root}")

    # 2. Drop and recreate SQLite tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✓ All SQLite relational tables dropped and recreated.")

    # 3. Recreate SQLite FTS5 search index
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS resume_search;"))
    initialize_search_index()
    print("✓ SQLite FTS5 full-text search index re-initialized.")
    print("✓ Database reset successfully to pristine empty state.")


def main():
    parser = argparse.ArgumentParser(description="Reset Tandem database and storage.")
    parser.add_argument(
        "--reseed",
        action="store_true",
        help="Re-seed the 25 candidates and 3 employer organizations after reset.",
    )
    args = parser.parse_args()

    reset_environment()

    if args.reseed:
        seeder_path = Path(__file__).parent / "seed_test_dataset.py"
        print(f"\nTriggering seeder script: {seeder_path} ...")
        subprocess.run([sys.executable, str(seeder_path)], check=True)


if __name__ == "__main__":
    main()

