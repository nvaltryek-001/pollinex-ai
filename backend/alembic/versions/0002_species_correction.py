"""keep original species prediction when a user corrects it

Revision ID: 0002_species_correction
Revises: 0001_initial
Create Date: 2026-11-03
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_species_correction"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("flower_detections") as b:
        b.add_column(sa.Column("species_original", sa.String(40), nullable=True))
        b.add_column(sa.Column("species_original_confidence", sa.Float, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("flower_detections") as b:
        b.drop_column("species_original_confidence")
        b.drop_column("species_original")
