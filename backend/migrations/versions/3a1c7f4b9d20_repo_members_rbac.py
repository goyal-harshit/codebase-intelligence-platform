"""repo_members rbac table

Revision ID: 3a1c7f4b9d20
Revises: 2e702f0b6396
Create Date: 2026-06-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a1c7f4b9d20'
down_revision: Union[str, None] = '2e702f0b6396'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'repo_members',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('repo_id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repo_id'], ['repos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repo_id', 'user_id', name='uq_repo_member'),
    )
    op.create_index(op.f('ix_repo_members_repo_id'), 'repo_members', ['repo_id'])
    op.create_index(op.f('ix_repo_members_user_id'), 'repo_members', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_repo_members_user_id'), table_name='repo_members')
    op.drop_index(op.f('ix_repo_members_repo_id'), table_name='repo_members')
    op.drop_table('repo_members')
