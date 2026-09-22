"""CityTriage: роли пользователей, удаление примера Item

Revision ID: c0a1b2c3d4e5
Revises: fe56fa70289e
Create Date: 2026-09-21

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "c0a1b2c3d4e5"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("role", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=False, server_default="citizen"),
    )
    op.add_column("user", sa.Column("crew_id", sqlmodel.sql.sqltypes.AutoString(length=32), nullable=True))
    op.drop_table("item")


def downgrade():
    op.create_table(
        "item",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_column("user", "crew_id")
    op.drop_column("user", "role")
