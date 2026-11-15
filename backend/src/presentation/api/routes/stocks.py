"""Эндпоинты складских остатков и товаров в пути."""

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


@router.get(
    "",
    response_model=OverviewResponse,
    summary="Экран остатков",
    response_description="Остатки по SKU и складу: физический, резерв, доступно, итоги, в пути.",
)
async def stocks_overview(
    sku: str | None = Query(default=None, description="Фильтр по SKU (подстрока)"),
    name: str | None = Query(default=None, description="Фильтр по названию товара (подстрока)"),
    uow: UnitOfWork = Depends(get_uow),
) -> OverviewResponse:
    """Главный экран: для каждого товара — разбивка по складам и итоговые остатки.

    `available = physical - reserved`; товар в пути (`in_transit`) показан отдельно
    по типам: внутреннее перемещение, FBO, FBS.
    """
    data = await GetStocksOverviewUseCase().execute(uow, sku=sku, name=name)
    return _overview(data)


@router.get(
    "/in-transit",
    response_model=InTransitResponse,
    summary="Товары в пути",
    response_description="Сводка по товарам в пути с разбивкой: перемещение / FBO / FBS.",
)
async def in_transit(uow: UnitOfWork = Depends(get_uow)) -> InTransitResponse:
    """Возвращает товары, которые уже покинули ФФ, но ещё не приняты/доставлены."""
    data = await GetInTransitUseCase().execute(uow)
    return InTransitResponse(items=data["items"])


@router.get(
    "/{sku}",
    response_model=OverviewResponse,
    summary="Остатки по SKU",
    response_description="Остатки конкретного артикула по всем складам.",
)
async def stock_by_sku(sku: str, uow: UnitOfWork = Depends(get_uow)) -> OverviewResponse:
    """Возвращает остатки одного артикула; 404, если SKU не найден."""
    data = await GetStockBySkuUseCase().execute(uow, sku)
    return _overview(data)
