"""clear warehouse FK from archive operations

Revision ID: 0003_clear_archive_wh_fk
Revises: 0002_warehouse_name_unique
Create Date: 2026-11-16

У операций WAREHOUSE_ARCHIVE не должно быть ссылки source/target_warehouse_id:
архивирование — это маркер, а не использование склада. Такая ссылка мешала бы
полному удалению архивированного склада.
"""

from __future__ import annotations

from alembic import op

revision = "0003_clear_archive_wh_fk"
down_revision = "0002_warehouse_name_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE operations "
        "SET source_warehouse_id = NULL, target_warehouse_id = NULL "
        "WHERE type = 'WAREHOUSE_ARCHIVE'"
    )


def downgrade() -> None:
    # Восстанавливаем ссылку из entity_id (для операций архивирования склада).
    op.execute(
        "UPDATE operations "
        "SET source_warehouse_id = entity_id "
        "WHERE type = 'WAREHOUSE_ARCHIVE' AND entity_type = 'warehouse'"
    )
