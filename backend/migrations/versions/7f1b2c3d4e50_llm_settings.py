"""llm_settings

Revision ID: 7f1b2c3d4e50
Revises: 5704ea2f23d2
Create Date: 2026-07-01 18:30:00.000000

App-wide LLM provider configuration (plan Phase C). Single-row override table;
the API key is stored encrypted at rest.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f1b2c3d4e50'
down_revision: Union[str, None] = '5704ea2f23d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'llm_settings',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('base_url', sa.String(length=2048), nullable=True),
        sa.Column('model', sa.String(length=255), nullable=True),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('llm_settings')
