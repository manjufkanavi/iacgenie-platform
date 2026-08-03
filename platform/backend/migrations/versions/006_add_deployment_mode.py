"""add deployment_mode to pipelines

Revision ID: 006
Revises: 005
Create Date: 2026-05-26 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add deployment_mode column to pipelines table
    op.add_column(
        "pipelines", sa.Column("deployment_mode", sa.String(length=32), nullable=True)
    )


def downgrade() -> None:
    # Drop deployment_mode column
    op.drop_column("pipelines", "deployment_mode")
