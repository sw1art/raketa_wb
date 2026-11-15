"""Эндпоинты каталога товаров.

Контроллеры тонкие: принимают запрос, вызывают use case и возвращают результат.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from application.commands import CreateProductCommand, ListQuery, UpdateProductCommand
from application.use_cases import (
    CreateProductUseCase,
    GetProductUseCase,
    ListProductsUseCase,
    UpdateProductUseCase,
)
from domain.repositories.interfaces import UnitOfWork
from presentation.api.dependencies import get_uow
from presentation.api.schemas import (
    CreateProductRequest,
    PaginatedProducts,
    ProductOut,
    UpdateProductRequest,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=PaginatedProducts,
    summary="Список товаров",
    response_description="Пагинированный список товаров с фильтром по SKU и названию.",
)
async def list_products(
    sku: str | None = Query(
        default=None, description="Фильтр по SKU (подстрока, без учёта регистра)"
    ),
    name: str | None = Query(
        default=None, description="Фильтр по названию (подстрока, без учёта регистра)"
    ),
    offset: int = Query(default=0, ge=0, description="Смещение для пагинации"),
    limit: int = Query(default=50, ge=1, le=500, description="Размер страницы (1–500)"),
    uow: UnitOfWork = Depends(get_uow),
) -> PaginatedProducts:
    """Возвращает товары с пагинацией и фильтрацией по `sku`/`name`."""
    products, total = await ListProductsUseCase().execute(
        uow, sku=sku, name=name, query=ListQuery(offset=offset, limit=limit)
    )
    return PaginatedProducts(items=[ProductOut.model_validate(p) for p in products], total=total)


@router.get(
    "/{product_id}",
    response_model=ProductOut,
    summary="Информация о товаре",
    response_description="Данные одного товара по его UUID.",
)
async def get_product(product_id: UUID, uow: UnitOfWork = Depends(get_uow)) -> ProductOut:
    """Возвращает товар по идентификатору; 404, если товар не найден."""
    product = await GetProductUseCase().execute(uow, product_id)
    return ProductOut.model_validate(product)


@router.post(
    "",
    response_model=ProductOut,
    status_code=201,
    summary="Создать товар",
    response_description="Созданный товар. SKU уникален в пределах магазина.",
)
async def create_product(
    body: CreateProductRequest, uow: UnitOfWork = Depends(get_uow)
) -> ProductOut:
    """Создаёт товар. Если магазин не указан, используется магазин по умолчанию (из seed).

    Дублирование SKU в рамках магазина возвращает 409.
    """
    product = await CreateProductUseCase().execute(
        uow,
        CreateProductCommand(sku=body.sku, name=body.name, wb_external_id=body.wb_external_id),
    )
    return ProductOut.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    summary="Изменить товар",
    response_description="Обновлённый товар.",
)
async def update_product(
    product_id: UUID, body: UpdateProductRequest, uow: UnitOfWork = Depends(get_uow)
) -> ProductOut:
    """Частично обновляет товар (название, SKU, внешний ID Wildberries)."""
    product = await UpdateProductUseCase().execute(
        uow,
        UpdateProductCommand(
            product_id=product_id,
            name=body.name,
            sku=body.sku,
            wb_external_id=body.wb_external_id,
        ),
    )
    return ProductOut.model_validate(product)
