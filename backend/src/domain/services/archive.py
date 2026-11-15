"""Warehouse archival policy — business rules for logical deletion."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class NonZeroStock:
    product_id: UUID
    sku: str
    product_name: str
    physical: int


@dataclass
class ArchiveCheck:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    nonzero_stocks: list[NonZeroStock] = field(default_factory=list)


def check_archive(
    nonzero_stocks: list[NonZeroStock],
    open_transfers: int,
    open_shipments: int,
    active_reservations: int,
) -> ArchiveCheck:
    reasons: list[str] = []
    if nonzero_stocks:
        reasons.append(
            f"warehouse has {len(nonzero_stocks)} SKU(s) with non-zero physical stock"
        )
    if open_transfers:
        reasons.append(f"{open_transfers} unfinished transfer(s) reference this warehouse")
    if open_shipments:
        reasons.append(f"{open_shipments} unfinished shipment(s) reference this warehouse")
    if active_reservations:
        reasons.append(f"{active_reservations} active reservation(s) reference this warehouse")
    return ArchiveCheck(
        allowed=not reasons,
        reasons=reasons,
        nonzero_stocks=nonzero_stocks,
    )
