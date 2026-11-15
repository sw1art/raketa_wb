"""API router aggregation."""
from __future__ import annotations

from fastapi import APIRouter

from .history import router as history_router
from .listings import router as listings_router
from .operations import router as operations_router
from .products import router as products_router
from .shipments import router as shipments_router
from .stocks import router as stocks_router
from .warehouses import router as warehouses_router
from .wildberries import router as wildberries_router

api_router = APIRouter()
api_router.include_router(products_router)
api_router.include_router(warehouses_router)
api_router.include_router(stocks_router)
api_router.include_router(operations_router)
api_router.include_router(shipments_router)
api_router.include_router(listings_router)
api_router.include_router(history_router)
api_router.include_router(wildberries_router)
