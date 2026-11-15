"""Wildberries integration models."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from domain.enums import WbSyncStatus

from .base import Base


class WbSyncLog(Base):
    __tablename__ = "wb_sync_logs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    status: Mapped[WbSyncStatus] = mapped_column(
        Enum(WbSyncStatus, name="wb_sync_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
