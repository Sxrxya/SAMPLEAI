"""resume upload idempotency

Revision ID: 724f56446705
Revises: c6875f43348b
Create Date: 2026-11-10 14:22:16.032651

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '724f56446705'
down_revision: str | Sequence[str] | None = "c6875f43348b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "resume_versions",
        sa.Column("upload_idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "uq_resume_versions_upload_idempotency_key",
        "resume_versions",
        ["upload_idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_resume_versions_upload_idempotency_key", table_name="resume_versions")
    op.drop_column("resume_versions", "upload_idempotency_key")
