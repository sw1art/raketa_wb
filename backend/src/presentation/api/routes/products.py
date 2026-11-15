"""Product routes."""
from __future__ import annotations

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


@router.get("", response_model=PaginatedProducts)
async def list_products(
    sku: str | None = Query(default=None),
    name: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    uow: UnitOfWork = Depends(get_uow),
):
    products, total = await ListProductsUseCase().execute(
        uow, sku=sku, name=name, query=ListQuery(offset=offset, limit=limit)
    )
    return PaginatedProducts(
        items=[ProductOut.model_validate(p) for p in products], total=total
    )


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: UUID, uow: UnitOfWork = Depends(get_uow)
):
    product = await GetProductUseCase().execute(uow, product_id)
    return ProductOut.model_validate(product)


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    body: CreateProductRequest, uow: UnitOfWork = Depends(get_uow)
):
    product = await CreateProductUseCase().execute(
        uow,
        CreateProductCommand(
            sku=body.sku, name=body.name, wb_external_id=body.wb_external_id
        ),
    )
    return ProductOut.model_validate(product)


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID, body: UpdateProductRequest, uow: UnitOfWork = Depends(get_uow)
):
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
