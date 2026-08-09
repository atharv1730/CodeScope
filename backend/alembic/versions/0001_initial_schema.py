"""initial schema: analyses, file_metrics, contributors, dependencies, file_connections

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ANALYSIS_STATUS = postgresql.ENUM(
    "queued",
    "cloning",
    "analyzing_structure",
    "analyzing_git",
    "analyzing_complexity",
    "analyzing_dependencies",
    "complete",
    "failed",
    name="analysis_status",
    # We create the type explicitly in upgrade(); don't let the column
    # definition emit a second CREATE TYPE (which would error on real Postgres).
    create_type=False,
)


def upgrade() -> None:
    ANALYSIS_STATUS.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("repo_url", sa.String(1024), nullable=False),
        sa.Column("repo_name", sa.String(512), nullable=True),
        sa.Column("status", ANALYSIS_STATUS, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("commit_count", sa.Integer(), nullable=True),
        sa.Column("contributor_count", sa.Integer(), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=True),
        sa.Column("total_lines", sa.Integer(), nullable=True),
        sa.Column("primary_language", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analyses_repo_url", "analyses", ["repo_url"])
    op.create_index("ix_analyses_status", "analyses", ["status"])

    op.create_table(
        "file_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path", sa.String(2048), nullable=False),
        sa.Column("language", sa.String(128), nullable=True),
        sa.Column("lines_of_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blank_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("complexity_score", sa.Float(), nullable=True),
        sa.Column("function_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("change_frequency", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_changed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("top_contributor", sa.String(512), nullable=True),
    )
    op.create_index("ix_file_metrics_analysis_id", "file_metrics", ["analysis_id"])

    op.create_table(
        "contributors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(512), nullable=True),
        sa.Column("email", sa.String(512), nullable=True),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_commit", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_commit", sa.DateTime(timezone=True), nullable=True),
        sa.Column("files_touched", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_contributors_analysis_id", "contributors", ["analysis_id"])

    op.create_table(
        "dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("current_version", sa.String(128), nullable=True),
        sa.Column("latest_version", sa.String(128), nullable=True),
        sa.Column("is_outdated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("versions_behind", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_vulnerability", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("vulnerability_details", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_dependencies_analysis_id", "dependencies", ["analysis_id"])

    op.create_table(
        "file_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_file", sa.String(2048), nullable=False),
        sa.Column("target_file", sa.String(2048), nullable=False),
        sa.Column("connection_type", sa.String(32), nullable=False),
    )
    op.create_index("ix_file_connections_analysis_id", "file_connections", ["analysis_id"])
    op.create_index("ix_file_connections_type", "file_connections", ["connection_type"])


def downgrade() -> None:
    op.drop_table("file_connections")
    op.drop_table("dependencies")
    op.drop_table("contributors")
    op.drop_table("file_metrics")
    op.drop_table("analyses")
    ANALYSIS_STATUS.drop(op.get_bind(), checkfirst=True)
