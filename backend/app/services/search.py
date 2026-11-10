import json
import math

from sqlalchemy import exists, select, text
from sqlalchemy.orm import Session

from app.core.db import engine
from app.models import EmbeddingRecord, Resume, ResumeConsent, ResumeExtraction, ResumeVersion


def initialize_search_index() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS resume_search USING "
                "fts5(resume_version_id UNINDEXED, candidate_id UNINDEXED, searchable_text, "
                "tokenize='unicode61 remove_diacritics 2')"
            )
        )


def normalize_query(value: str) -> str:
    tokens = [token.replace('"', "") for token in value.split()]
    return " OR ".join(f'"{token}"' for token in tokens if token)


def upsert_resume_search(
    db: Session, *, resume_version_id: str, candidate_id: str, searchable_text: str
) -> None:
    db.execute(
        text("DELETE FROM resume_search WHERE resume_version_id = :resume_id"),
        {"resume_id": resume_version_id},
    )
    db.execute(
        text(
            "INSERT INTO resume_search(resume_version_id, candidate_id, searchable_text) "
            "VALUES (:resume_id, :candidate_id, :searchable_text)"
        ),
        {
            "resume_id": resume_version_id,
            "candidate_id": candidate_id,
            "searchable_text": searchable_text[:100_000],
        },
    )


def eligible_resume_search(db: Session, query: str, limit: int) -> list[dict]:
    match_query = normalize_query(query)
    if not match_query:
        return []
    results = db.execute(
        text(
            """
                 SELECT rs.resume_version_id, rs.candidate_id, rs.searchable_text,
                     bm25(resume_search) AS rank
                        FROM resume_search AS rs
                        JOIN resume_versions AS rv ON rv.id = rs.resume_version_id
            WHERE resume_search MATCH :match_query
              AND rv.status = 'complete'
                            AND EXISTS (
                                SELECT 1 FROM resume_extractions AS re
                                WHERE re.resume_version_id = rv.id
                                    AND re.review_status IN ('confirmed', 'corrected')
                            )
                            AND EXISTS (
                                SELECT 1 FROM resume_consents AS rc
                                WHERE rc.resume_version_id = rv.id
                                    AND rc.scope = 'recruiter_search' AND rc.revoked_at IS NULL
                            )
            ORDER BY rank ASC
            LIMIT :limit
            """
        ),
        {"match_query": match_query, "limit": limit},
    ).mappings()
    return [dict(row) for row in results]


def eligible_resume_embeddings(db: Session, model_id: str, limit: int = 10_000) -> list[dict]:
    has_reviewed_extraction = exists(
        select(ResumeExtraction.id).where(
            ResumeExtraction.resume_version_id == ResumeVersion.id,
            ResumeExtraction.review_status.in_(["confirmed", "corrected"]),
        )
    )
    has_active_consent = exists(
        select(ResumeConsent.id).where(
            ResumeConsent.resume_version_id == ResumeVersion.id,
            ResumeConsent.scope == "recruiter_search",
            ResumeConsent.revoked_at.is_(None),
        )
    )
    rows = db.execute(
        select(
            EmbeddingRecord.entity_id.label("resume_version_id"),
            Resume.candidate_id,
            EmbeddingRecord.vector_json,
        )
        .join(ResumeVersion, ResumeVersion.id == EmbeddingRecord.entity_id)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(
            EmbeddingRecord.entity_type == "resume_version",
            EmbeddingRecord.model_id == model_id,
            ResumeVersion.status == "complete",
            has_reviewed_extraction,
            has_active_consent,
        )
        .limit(limit)
    ).mappings()
    return [dict(row) for row in rows]


def cosine_similarity(left: list[float], right: list[float]) -> float | None:
    if not left or len(left) != len(right):
        return None
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return None
    return dot / (left_norm * right_norm)


def vector_from_json(value: list[float] | str) -> list[float]:
    if isinstance(value, str):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise ValueError("embedding is not a JSON list")
        return [float(item) for item in parsed]
    return [float(item) for item in value]
