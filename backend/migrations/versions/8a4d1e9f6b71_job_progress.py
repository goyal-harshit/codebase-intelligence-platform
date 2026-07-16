"""job_progress

Revision ID: 8a4d1e9f6b71
Revises: 7f1b2c3d4e50
Create Date: 2026-07-04 00:00:00.000000

Adds jobs.progress (0-100 within the current step) so the ingest status
endpoint can report a percentage instead of just a step name.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a4d1e9f6b71'
down_revision: Union[str, None] = '7f1b2c3d4e50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('progress', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'progress')
