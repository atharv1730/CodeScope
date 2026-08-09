"""git data: file_metrics.bus_factor, file_connections.weight, commit_activity

Revision ID: 0002_git_data
Revises: 0001_initial
Create Date: 2026-08-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_git_data"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_metrics",
        sa.Column("bus_factor", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "file_connections",
        sa.Column("weight", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "commit_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("author_email", sa.String(512), nullable=True),
        sa.Column("author_name", sa.String(512), nullable=True),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_commit_activity_analysis_id", "commit_activity", ["analysis_id"])


def downgrade() -> None:
    op.drop_table("commit_activity")
    op.drop_column("file_connections", "weight")
    op.drop_column("file_metrics", "bus_factor")
