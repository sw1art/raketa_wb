"""Unit tests for warehouse archive policy."""

from __future__ import annotations

from uuid import uuid4

from domain.services.archive import NonZeroStock, check_archive, check_purge


def test_archive_allowed_when_empty():
    check = check_archive([], 0, 0, 0)
    assert check.allowed is True
    assert check.reasons == []


def test_archive_blocked_by_nonzero_stock():
    ns = [NonZeroStock(product_id=uuid4(), sku="SKU-101", product_name="Органайзер", physical=10)]
    check = check_archive(ns, 0, 0, 0)
    assert check.allowed is False
    assert any("non-zero" in r for r in check.reasons)
    assert check.nonzero_stocks == ns


def test_archive_blocked_by_open_operations():
    check = check_archive([], open_transfers=2, open_shipments=1, active_reservations=3)
    assert check.allowed is False
    assert len(check.reasons) == 3
    assert any("transfer" in r for r in check.reasons)
    assert any("shipment" in r for r in check.reasons)
    assert any("reservation" in r for r in check.reasons)


def test_archive_blocked_multiple_reasons():
    ns = [NonZeroStock(product_id=uuid4(), sku="SKU-102", product_name="Контейнер", physical=4)]
    check = check_archive(ns, open_transfers=1, open_shipments=0, active_reservations=0)
    assert check.allowed is False
    assert len(check.reasons) == 2


def test_purge_allowed_when_no_references():
    check = check_purge({"stocks": 0, "operations": 0, "movements": 0})
    assert check.allowed is True
    assert check.references == {}


def test_purge_blocked_when_references_exist():
    check = check_purge({"stocks": 0, "operations": 3, "movements": 2})
    assert check.allowed is False
    assert check.references == {"operations": 3, "movements": 2}
