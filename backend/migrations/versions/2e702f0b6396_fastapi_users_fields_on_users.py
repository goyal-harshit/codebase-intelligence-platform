"""fastapi-users fields on users

Revision ID: 2e702f0b6396
Revises: 0be39c2d8218
Create Date: 2026-06-28 22:36:39.021584

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e702f0b6396'
down_revision: Union[str, None] = '0be39c2d8218'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table makes the ALTERs work on SQLite too (Postgres runs them
    # directly). server_default lets the NOT NULL column be added to a populated
    # table; FastAPI-Users sets is_verified explicitly thereafter.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("is_verified", sa.Boolean(), nullable=False,
                                   server_default=sa.false()))
        batch.alter_column("hashed_password",
                           existing_type=sa.VARCHAR(length=255),
                           type_=sa.String(length=1024),
                           nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("hashed_password",
                           existing_type=sa.String(length=1024),
                           type_=sa.VARCHAR(length=255),
                           nullable=True)
        batch.drop_column("is_verified")
