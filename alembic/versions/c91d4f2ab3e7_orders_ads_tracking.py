"""orders add gclid + ads_uploaded_at (Google Ads conversion tracking)

Revision ID: c91d4f2ab3e7
Revises: b461d9d676f9
Create Date: 2026-11-05 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c91d4f2ab3e7'
down_revision: Union[str, None] = 'b461d9d676f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column(
        'gclid', sa.String(length=255), nullable=False, server_default='',
        comment='Google Ads 点击 ID（landing_site 提取，转化回传键）'))
    op.add_column('orders', sa.Column(
        'ads_uploaded_at', sa.DateTime(), nullable=True,
        comment='转化回传 Google Ads 时间（空=未回传）'))
    op.create_index('ix_orders_gclid', 'orders', ['gclid'])


def downgrade() -> None:
    op.drop_index('ix_orders_gclid', table_name='orders')
    op.drop_column('orders', 'ads_uploaded_at')
    op.drop_column('orders', 'gclid')
