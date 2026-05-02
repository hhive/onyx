"""add sub2api user credential

Revision ID: 4f2b7c8d9e10
Revises: 14162713706c
Create Date: 2026-05-02 00:36:00.000000

"""

from alembic import op
import sqlalchemy as sa

from onyx.db.models import EncryptedString


# revision identifiers, used by Alembic.
revision = "4f2b7c8d9e10"
down_revision = "14162713706c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub2api_user_credential",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("sub2api_user_id", sa.Integer(), nullable=False),
        sa.Column("api_key_id", sa.Integer(), nullable=False),
        sa.Column("api_key", EncryptedString(), nullable=False),
        sa.Column("api_base_url", sa.Text(), nullable=False),
        sa.Column("text_model_name", sa.Text(), nullable=False),
        sa.Column("image_model_name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("sub2api_user_credential")
