import argparse
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings


def sqlite_path(database_url: str) -> Path:
    if not database_url.startswith("sqlite:///"):
        raise ValueError("SQLite backup utility only supports SQLite database URLs")
    return Path(database_url.removeprefix("sqlite:///"))


def backup_database(destination_dir: Path) -> Path:
    source_path = sqlite_path(get_settings().database_url).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Database file not found: {source_path}")
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_dir / f"recruitment-{stamp}.db"
    temporary = destination.with_suffix(".db.tmp")
    try:
        with sqlite3.connect(source_path) as source, sqlite3.connect(temporary) as target:
            source.backup(target)
        with sqlite3.connect(temporary) as check:
            result = check.execute("PRAGMA integrity_check").fetchone()
        if result is None or result[0] != "ok":
            raise RuntimeError("SQLite backup integrity check failed")
        os.replace(temporary, destination)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a consistent SQLite online backup")
    parser.add_argument("destination", type=Path, help="Backup directory")
    args = parser.parse_args()
    print(backup_database(args.destination))


if __name__ == "__main__":
    main()