"""End-to-end API tests (HTTP layer through ASGI transport).

Проверяют контракт API целиком: маршрутизацию, валидацию, статус-коды, единый
формат ошибок, идемпотентность и security-заголовки.
"""

from __future__ import annotations

from tests.integration.helpers import seed_catalog, set_stock


async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_security_headers(client):
    resp = await client.get("/healthz")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-request-id"]


async def test_stocks_overview(client, session_factory):
    await seed_catalog(session_factory)
    resp = await client.get("/api/v1/stocks")
    assert resp.status_code == 200
    body = resp.json()
    assert {w["name"] for w in body["warehouses"]} == {"Север", "Юг"}
    skus = {p["sku"] for p in body["products"]}
    assert {"SKU-101", "SKU-102", "SKU-103"} <= skus


async def test_receipt_and_idempotency(client, session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    payload = {"warehouse_id": str(ids["north"]), "product_id": str(ids["p101"]), "quantity": 5}
    first = await client.post(
        "/api/v1/operations/receipts",
        json=payload,
        headers={"Idempotency-Key": "e2e-receipt-1"},
    )
    assert first.status_code == 201
    assert first.json()["physical"] == 15

    # Повтор с тем же ключом не дублирует приход.
    second = await client.post(
        "/api/v1/operations/receipts",
        json=payload,
        headers={"Idempotency-Key": "e2e-receipt-1"},
    )
    assert second.status_code == 201
    assert second.json()["physical"] == 15

    overview = await client.get("/api/v1/stocks", params={"sku": "SKU-101"})
    row = overview.json()["products"][0]
    north = next(w for w in row["warehouses"] if w["warehouse_name"] == "Север")
    assert north["physical"] == 15


async def test_shortage_error_envelope(client, session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 2)
    await set_stock(session_factory, ids["p101"], ids["south"], 10)

    resp = await client.post(
        "/api/v1/operations/reservations",
        json={"warehouse_id": str(ids["north"]), "product_id": str(ids["p101"]), "quantity": 5},
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"]["code"] == "stock_shortage"
    assert body["error"]["detail"]["shortfall"] == 3
    assert body["request_id"]
    assert any(
        w["warehouse_id"] == str(ids["south"]) and w["available"] == 10
        for w in body["error"]["detail"]["other_warehouses"]
    )


async def test_archive_blocked(client, session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    resp = await client.delete(f"/api/v1/warehouses/{ids['north']}")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "warehouse_archive_error"


async def test_validation_error(client, session_factory):
    ids = await seed_catalog(session_factory)
    resp = await client.post(
        "/api/v1/operations/receipts",
        json={"warehouse_id": str(ids["north"]), "product_id": str(ids["p101"]), "quantity": 0},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_not_found(client):
    resp = await client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_history_endpoint(client, session_factory):
    ids = await seed_catalog(session_factory)
    await set_stock(session_factory, ids["p101"], ids["north"], 10)

    await client.post(
        "/api/v1/operations/receipts",
        json={"warehouse_id": str(ids["north"]), "product_id": str(ids["p101"]), "quantity": 5},
    )

    resp = await client.get("/api/v1/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    receipt = [e for e in body["items"] if e["operation_type"] == "RECEIPT"]
    assert receipt and receipt[0]["sku"] == "SKU-101"
