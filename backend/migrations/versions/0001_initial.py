"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-16

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

ENUMS: dict[str, list[str]] = {
    "operation_type": [
        "RECEIPT", "RESERVE", "RESERVE_CANCEL", "FBS_SHIP", "FBO_CREATE",
        "FBO_DISPATCH", "FBO_RECEIVE", "TRANSFER_CREATE", "TRANSFER_DISPATCH",
        "TRANSFER_RECEIVE", "WAREHOUSE_ARCHIVE",
    ],
    "movement_type": [
        "RECEIPT", "FBS_SHIP", "FBO_DISPATCH", "TRANSFER_DISPATCH", "TRANSFER_RECEIVE",
    ],
    "reservation_status": ["ACTIVE", "CANCELLED", "SHIPPED"],
    "transfer_status": ["DRAFT", "IN_TRANSIT", "RECEIVED", "CANCELLED"],
    "shipment_type": ["FBS", "FBO"],
    "shipment_status": ["DRAFT", "IN_TRANSIT", "SHIPPED", "RECEIVED", "CANCELLED"],
    "outbox_status": ["PENDING", "PUBLISHED", "FAILED"],
    "wb_sync_status": ["SUCCESS", "FAILED", "DEMO"],
}


def _uuid():
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    bind = op.get_bind()
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    op.create_table(
        "stores",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "warehouses",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "products",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("store_id", _uuid(), nullable=False),
        sa.Column("sku", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("wb_external_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "sku", name="uq_products_store_sku"),
    )
    op.create_index("ix_products_store_id", "products", ["store_id"])

    op.create_table(
        "stocks",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("warehouse_id", _uuid(), nullable=False),
        sa.Column("physical", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("reserved", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("physical >= 0", name="ck_stocks_physical_nonnegative"),
        sa.CheckConstraint("reserved >= 0", name="ck_stocks_reserved_nonnegative"),
        sa.CheckConstraint("reserved <= physical", name="ck_stocks_reserved_lte_physical"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "warehouse_id", name="uq_stocks_product_warehouse"),
    )
    op.create_index("ix_stocks_product_id", "stocks", ["product_id"])
    op.create_index("ix_stocks_warehouse_id", "stocks", ["warehouse_id"])

    op.create_table(
        "reservations",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("warehouse_id", _uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="reservation_status", create_type=False), nullable=False),
        sa.Column("operation_id", _uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_reservations_quantity_positive"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_product_id", "reservations", ["product_id"])
    op.create_index("ix_reservations_warehouse_id", "reservations", ["warehouse_id"])

    op.create_table(
        "transfers",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("source_warehouse_id", _uuid(), nullable=False),
        sa.Column("target_warehouse_id", _uuid(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="transfer_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfers_source_warehouse_id", "transfers", ["source_warehouse_id"])
    op.create_index("ix_transfers_target_warehouse_id", "transfers", ["target_warehouse_id"])

    op.create_table(
        "transfer_items",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("transfer_id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_transfer_items_quantity_positive"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["transfer_id"], ["transfers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_items_transfer_id", "transfer_items", ["transfer_id"])

    op.create_table(
        "shipments",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("type", postgresql.ENUM(name="shipment_type", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM(name="shipment_status", create_type=False), nullable=False),
        sa.Column("source_warehouse_id", _uuid(), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("external_status", sa.String(length=128), nullable=True),
        sa.Column("reservation_id", _uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id"),
    )
    op.create_index("ix_shipments_source_warehouse_id", "shipments", ["source_warehouse_id"])

    op.create_table(
        "shipment_items",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("shipment_id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_shipment_items_quantity_positive"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipment_items_shipment_id", "shipment_items", ["shipment_id"])

    op.create_table(
        "operations",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("type", postgresql.ENUM(name="operation_type", create_type=False), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'SUCCESS'")),
        sa.Column("source_warehouse_id", _uuid(), nullable=True),
        sa.Column("target_warehouse_id", _uuid(), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", _uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_operations_type", "operations", ["type"])
    op.create_index("ix_operations_created_at", "operations", ["created_at"])

    op.create_table(
        "operation_items",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("operation_id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("source_warehouse_id", _uuid(), nullable=True),
        sa.Column("target_warehouse_id", _uuid(), nullable=True),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operation_items_operation_id", "operation_items", ["operation_id"])

    op.create_table(
        "stock_movements",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("movement_type", postgresql.ENUM(name="movement_type", create_type=False), nullable=False),
        sa.Column("source_warehouse_id", _uuid(), nullable=True),
        sa.Column("target_warehouse_id", _uuid(), nullable=True),
        sa.Column("operation_id", _uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["operation_id"], ["operations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_index("ix_stock_movements_movement_type", "stock_movements", ["movement_type"])
    op.create_index("ix_stock_movements_operation_id", "stock_movements", ["operation_id"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", _uuid(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", _uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", postgresql.ENUM(name="outbox_status", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.String(length=2048), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_outbox_events_pending", "outbox_events", ["status", "next_retry_at", "created_at"])

    op.create_table(
        "processed_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("consumer_name", sa.String(length=128), nullable=False),
        sa.Column("event_id", _uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consumer_name", "event_id", name="uq_processed_events_consumer_event"),
    )

    op.create_table(
        "wb_sync_logs",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="wb_sync_status", create_type=False), nullable=False),
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error", sa.String(length=2048), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("wb_sync_logs")
    op.drop_table("processed_events")
    op.drop_table("outbox_events")
    op.drop_table("stock_movements")
    op.drop_table("operation_items")
    op.drop_table("operations")
    op.drop_table("shipment_items")
    op.drop_table("shipments")
    op.drop_table("transfer_items")
    op.drop_table("transfers")
    op.drop_table("reservations")
    op.drop_table("stocks")
    op.drop_table("products")
    op.drop_table("warehouses")
    op.drop_table("stores")

    bind = op.get_bind()
    for name in reversed(list(ENUMS)):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
