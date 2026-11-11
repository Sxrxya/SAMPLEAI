from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def resolve_database_url(url: str) -> str:
    if url.startswith("sqlite:///./data/"):
        here_db = Path("./data/recruitment.db")
        parent_db = Path("../data/recruitment.db")
        if not here_db.exists() and parent_db.exists():
            return f"sqlite:///{parent_db.resolve().as_posix()}"
        elif here_db.exists():
            return f"sqlite:///{here_db.resolve().as_posix()}"
    return url


def build_engine(database_url: str) -> Engine:
    database_url = resolve_database_url(database_url)
    connect_args = (
        {"check_same_thread": False, "timeout": 30} if database_url.startswith("sqlite") else {}
    )
    if database_url.startswith("sqlite:") and ":memory:" not in database_url:
        db_path = database_url.removeprefix("sqlite:///")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
