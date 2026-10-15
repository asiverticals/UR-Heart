"""add peer_incinerated to chk_matches_closure_status

Revision ID: 20261015_0001
Revises: 
Create Date: 2026-10-15 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261015_0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing check constraint and re-add with 'peer_incinerated'
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_constraint('chk_matches_closure_status', type_='check')
        batch_op.create_check_constraint(
            'chk_matches_closure_status',
            "closure_status IN ('active', 'closed_with_grace', 'unmatched', 'peer_incinerated')",
        )


def downgrade() -> None:
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_constraint('chk_matches_closure_status', type_='check')
        batch_op.create_check_constraint(
            'chk_matches_closure_status',
            "closure_status IN ('active', 'closed_with_grace', 'unmatched')",
        )
