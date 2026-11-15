"""Stock routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from application.use_cases import (
    GetInTransitUseCase,
    GetStockBySkuUseCase,
    GetStocksOverviewUseCase,
)
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import (
    InTransitResponse,
    OverviewResponse,
    StockRowOut,
    WarehouseOut,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


def _overview(data: dict) -> OverviewResponse:
    return OverviewResponse(
        warehouses=[WarehouseOut.model_validate(w) for w in data["warehouses"]],
        products=[StockRowOut.model_validate(p) for p in data["products"]],
    )


@router.get("", response_model=OverviewResponse)
async def stocks_overview(
    sku: str | None = Query(default=None),
    name: str | None = Query(default=None),
    uow: UnitOfWork = Depends(get_uow),
):
    data = await GetStocksOverviewUseCase().execute(uow, sku=sku, name=name)
    return _overview(data)


@router.get("/in-transit", response_model=InTransitResponse)
async def in_transit(uow: UnitOfWork = Depends(get_uow)):
    data = await GetInTransitUseCase().execute(uow)
    return InTransitResponse(items=data["items"])


@router.get("/{sku}", response_model=OverviewResponse)
async def stock_by_sku(sku: str, uow: UnitOfWork = Depends(get_uow)):
    data = await GetStockBySkuUseCase().execute(uow, sku)
    return _overview(data)
