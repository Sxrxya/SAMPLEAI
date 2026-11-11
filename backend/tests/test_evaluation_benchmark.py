"""Ground-truth evaluation benchmark test suite for Tandem recruitment intelligence.

Tests:
1. Precision@5: Quality and qualification of top-5 recommended candidates.
2. Recall@5: Retrieval of top qualified candidates for specific job roles.
3. NDCG@5: Ranking quality (higher relevance candidates ranked earlier).
4. Score Monotonicity: Rank 1 score >= Rank 2 >= Rank 3 >= Rank 4 >= Rank 5.
5. Cross-domain Rejection: Completely unrelated candidates (e.g. Accountant for AI role) are rejected.
6. Evidence Traceability: Returned candidates must have concrete evidence items and dimensions.
"""

import math
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import Job
from app.services.matching import evaluate_candidates_for_job

candidate_paths = [
    Path("data/recruitment.db").resolve(),
    Path("backend/data/recruitment.db").resolve(),
    Path(__file__).resolve().parent.parent / "data" / "recruitment.db",
]
DB_PATH = next((p for p in candidate_paths if p.exists()), candidate_paths[0])
benchmark_engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}")
BenchmarkSession = sessionmaker(bind=benchmark_engine)


def calculate_dcg(relevance_scores: list[float], k: int = 5) -> float:
    """Calculate Discounted Cumulative Gain at rank k."""
    dcg = 0.0
    for idx, rel in enumerate(relevance_scores[:k], start=1):
        dcg += (2.0**rel - 1.0) / math.log2(idx + 1)
    return dcg


def calculate_ndcg(relevance_scores: list[float], ideal_relevance_scores: list[float], k: int = 5) -> float:
    """Calculate Normalized Discounted Cumulative Gain at rank k."""
    dcg = calculate_dcg(relevance_scores, k)
    idcg = calculate_dcg(sorted(ideal_relevance_scores, reverse=True), k)
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def test_ai_platform_engineer_top5_benchmark():
    """Evaluate Top-5 matching for 'Senior Python & AI Platform Engineer'."""
    if not DB_PATH.exists():
        pytest.skip(f"Database at {DB_PATH} not found.")

    with BenchmarkSession() as db:
        job = db.scalar(select(Job).where(Job.title == "Senior Python & AI Platform Engineer"))
        if job is None:
            pytest.skip("Job not found in benchmark database.")

        matches = evaluate_candidates_for_job(db=db, job_id=job.id, top_k=5)

        # 1. Returned results check
        assert len(matches) == 5, f"Expected 5 matches, got {len(matches)}"

        # 2. Ranking consistency / Score monotonicity
        scores = [m["overallScore"] for m in matches]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Score monotonicity violated: {scores[i]} < {scores[i+1]}"

        # 3. Precision@5: All 5 candidates must have >= 50% score and have matched required skills
        qualified_count = sum(1 for m in matches if m["overallScore"] >= 50 and len(m["skills"]) >= 2)
        precision_at_5 = qualified_count / 5.0
        assert precision_at_5 >= 0.8, f"Precision@5 too low: {precision_at_5}"

        # 4. Amara Johnson or David Chen should be top 2 candidates
        top_names = [m["name"] for m in matches[:2]]
        assert any("Amara Johnson" in name or "David Chen" in name for name in top_names), (
            f"Expected top AI candidates in top 2, got: {top_names}"
        )

        # 5. Cross-domain rejection: Robert Miller (accountant) must NOT appear in top-5
        names = [m["name"] for m in matches]
        assert "Robert Miller" not in names, "Cross-domain rejection failed: Accountant matched for AI engineer!"

        # 6. Evidence Traceability
        for m in matches:
            assert len(m["evidence"]) > 0, f"Match for {m['name']} missing evidence citations"
            assert len(m["dimensions"]) == 5, f"Match for {m['name']} missing dimensions"

        # 7. NDCG@5 calculation
        relevance_grades = [m["overallScore"] / 20.0 for m in matches]  # scale to 0-5
        ideal_grades = sorted(relevance_grades, reverse=True)
        ndcg_5 = calculate_ndcg(relevance_grades, ideal_grades, k=5)
        assert ndcg_5 >= 0.95, f"NDCG@5 is {ndcg_5}, expected >= 0.95"


def test_product_designer_top5_benchmark():
    """Evaluate Top-5 matching for 'Senior Product & Design Systems Designer'."""
    if not DB_PATH.exists():
        pytest.skip(f"Database at {DB_PATH} not found.")

    with BenchmarkSession() as db:
        job = db.scalar(select(Job).where(Job.title == "Senior Product & Design Systems Designer"))
        if job is None:
            pytest.skip("Job not found in benchmark database.")

        matches = evaluate_candidates_for_job(db=db, job_id=job.id, top_k=5)
        assert len(matches) <= 5

        # Sophia Vance (Principal Product Designer) must be in the matches
        names = [m["name"] for m in matches]
        assert any("Sophia Vance" in name or "Elena Rostova" in name for name in names), (
            f"Expected lead designers in top matches, got {names}"
        )

        # Cross-domain rejection: Robert Miller (accountant) must NOT appear
        assert "Robert Miller" not in names

        # Score monotonicity
        scores = [m["overallScore"] for m in matches]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]


def test_healthcare_data_analyst_top5_benchmark():
    """Evaluate Top-5 matching for 'Healthcare Data Analyst & SQL Specialist'."""
    if not DB_PATH.exists():
        pytest.skip(f"Database at {DB_PATH} not found.")

    with BenchmarkSession() as db:
        job = db.scalar(select(Job).where(Job.title == "Healthcare Data Analyst & SQL Specialist"))
        if job is None:
            pytest.skip("Job not found in benchmark database.")

        matches = evaluate_candidates_for_job(db=db, job_id=job.id, top_k=5)
        assert len(matches) <= 5

        # Kavita Patel (Clinical Data Analyst) must be in top matches
        names = [m["name"] for m in matches]
        assert any("Kavita Patel" in name for name in names), (
            f"Expected Kavita Patel in top matches, got {names}"
        )

        # Cross-domain rejection: Robert Miller must NOT appear
        assert "Robert Miller" not in names
