"""Stock overview / in-transit query use cases."""

from __future__ import annotations

from collections import defaultdict

from domain.entities import Product, Warehouse
from domain.enums import ShipmentType
from domain.repositories.interfaces import UnitOfWork

from ..exceptions import NotFoundError
from .base import UseCase


async def _in_transit_breakdown(uow: UnitOfWork) -> dict:
    transfers = await uow.transfers.list_in_transit()
    shipments = await uow.shipments.list_in_transit()
    per_product: dict = defaultdict(lambda: {"transfer": 0, "fbo": 0, "fbs": 0})
    for transfer in transfers:
        for item in transfer.items:
            per_product[item.product_id]["transfer"] += item.quantity
    for shipment in shipments:
        key = "fbs" if shipment.type == ShipmentType.FBS else "fbo"
        for item in shipment.items:
            per_product[item.product_id][key] += item.quantity
    return per_product


def _stock_row(
    product: Product,
    warehouses: list[Warehouse],
    stock_map: dict,
    in_transit: dict,
) -> dict:
    warehouse_rows = []
    total_physical = total_reserved = 0
    for wh in warehouses:
        stock = stock_map.get((product.id, wh.id))
        physical = stock.physical if stock else 0
        reserved = stock.reserved if stock else 0
        total_physical += physical
        total_reserved += reserved
        warehouse_rows.append(
            {
                "warehouse_id": str(wh.id),
                "warehouse_name": wh.name,
                "physical": physical,
                "reserved": reserved,
                "available": physical - reserved,
            }
        )
    transit = in_transit.get(product.id, {"transfer": 0, "fbo": 0, "fbs": 0})
    return {
        "product_id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "wb_external_id": product.wb_external_id,
        "warehouses": warehouse_rows,
        "total_physical": total_physical,
        "total_reserved": total_reserved,
        "total_available": total_physical - total_reserved,
        "in_transit": dict(transit),
        "in_transit_total": transit["transfer"] + transit["fbo"] + transit["fbs"],
    }


class GetStocksOverviewUseCase(UseCase):
    async def _run(
        self,
        uow: UnitOfWork,
        *,
        sku: str | None = None,
        name: str | None = None,
    ) -> dict:
        products, _ = await uow.products.list(sku=sku, name=name, offset=0, limit=10_000)
        warehouses = await uow.warehouses.list(active_only=True)
        joined = await uow.stocks.list_joined(sku=sku, name=name, warehouse_id=None)
        stock_map = {(stock.product_id, stock.warehouse_id): stock for stock, _p, _w in joined}
        in_transit = await _in_transit_breakdown(uow)
        rows = [_stock_row(product, warehouses, stock_map, in_transit) for product in products]
        return {"warehouses": warehouses, "products": rows}


class GetStockBySkuUseCase(UseCase):
    async def _run(self, uow: UnitOfWork, sku: str) -> dict:
        products, _ = await uow.products.list(sku=sku, name=None, offset=0, limit=10)
        if not products:
            raise NotFoundError(f"no product with SKU '{sku}'")
        warehouses = await uow.warehouses.list(active_only=True)
        joined = await uow.stocks.list_joined(sku=sku, name=None, warehouse_id=None)
        stock_map = {(stock.product_id, stock.warehouse_id): stock for stock, _p, _w in joined}
        in_transit = await _in_transit_breakdown(uow)
        rows = [_stock_row(product, warehouses, stock_map, in_transit) for product in products]
        return {"warehouses": warehouses, "products": rows}


class GetInTransitUseCase(UseCase):
    async def _run(self, uow: UnitOfWork) -> dict:
        in_transit = await _in_transit_breakdown(uow)
        products, _ = await uow.products.list(sku=None, name=None, offset=0, limit=10_000)
        product_by_id = {p.id: p for p in products}
        rows = []
        for product_id, counts in in_transit.items():
            product = product_by_id.get(product_id)
            if product is None:
                continue
            rows.append(
                {
                    "product_id": str(product_id),
                    "sku": product.sku,
                    "name": product.name,
                    "transfer": counts["transfer"],
                    "fbo": counts["fbo"],
                    "fbs": counts["fbs"],
                    "total": counts["transfer"] + counts["fbo"] + counts["fbs"],
                }
            )
        rows.sort(key=lambda r: r["sku"])
        return {"items": rows}
