"""warehouse name uniqueness only among active warehouses

Revision ID: 0002_warehouse_name_unique
Revises: 0001_initial
Create Date: 2026-11-16

Разрешает повторное использование имени архивированного склада: имя уникально
только среди активных (не архивированных) складов.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_warehouse_name_unique"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("warehouses_name_key", "warehouses", type_="unique")
    op.create_index(
        "uq_warehouses_name_active",
        "warehouses",
        ["name"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_warehouses_name_active", table_name="warehouses")
    op.create_unique_constraint("warehouses_name_key", "warehouses", ["name"])
