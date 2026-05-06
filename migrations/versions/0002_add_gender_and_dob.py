"""Add gender and date_of_birth to users

Revision ID: 0002_add_gender_and_dob
Revises: 0001_d1_baseline
Create Date: 2026-05-05

Adds two profile fields needed by the Profile Settings screen.
Both are nullable — existing users won't be forced to backfill them.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_gender_and_dob"
down_revision: Union[str, None] = "0001_d1_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("gender", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("date_of_birth", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "date_of_birth")
    op.drop_column("users", "gender")
