"""add moneyforward_account_name to m_accounts

Revision ID: 076054a5d5ae
Revises: ab52946b0389
Create Date: 2026-07-07 20:50:46.124651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '076054a5d5ae'
down_revision: Union[str, Sequence[str], None] = 'ab52946b0389'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'm_accounts',
        sa.Column(
            'moneyforward_account_name',
            sa.String(),
            nullable=True,
            comment='マネーフォワードME連携時の口座表示名（CSVの「保有金融機関」列とのマッチングに使用。未設定の場合はaccount_nameで照合）',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('m_accounts', 'moneyforward_account_name')
