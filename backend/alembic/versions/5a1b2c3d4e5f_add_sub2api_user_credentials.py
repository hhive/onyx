"""Add Sub2API user credentials

Revision ID: 5a1b2c3d4e5f
Revises: 4d545225fd82
Create Date: 2026-05-31 12:57:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "5a1b2c3d4e5f"
down_revision = "4d545225fd82"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub2api_user_credential",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub2api_user_id", sa.Integer(), nullable=False),
        sa.Column("api_key", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_sub2api_user_credential_user_id"),
        sa.UniqueConstraint(
            "sub2api_user_id",
            name="uq_sub2api_user_credential_sub2api_user_id",
        ),
    )
    op.create_index(
        "ix_sub2api_user_credential_user_id",
        "sub2api_user_credential",
        ["user_id"],
    )
    op.create_index(
        "ix_sub2api_user_credential_sub2api_user_id",
        "sub2api_user_credential",
        ["sub2api_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sub2api_user_credential_sub2api_user_id",
        table_name="sub2api_user_credential",
    )
    op.drop_index(
        "ix_sub2api_user_credential_user_id",
        table_name="sub2api_user_credential",
    )
    op.drop_table("sub2api_user_credential")
