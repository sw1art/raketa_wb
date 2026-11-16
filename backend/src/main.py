"""Точка входа FastAPI-приложения CheckStock.

Собирает приложение: OpenAPI-метаданные, CORS, security-заголовки, обработчики
ошибок и API-роутеры.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from config.logging import configure_logging
from config.settings import get_settings
from infrastructure.database.session import dispose_engine, engine
from presentation.api.errors import register_exception_handlers
from presentation.api.routes import api_router

_settings = get_settings()

_DESCRIPTION = """
CheckStock — управление складскими остатками товаров на складах фулфилмента (ФФ),
резервами под FBS и отправками FBS/FBO на Wildberries.

**Главный инвариант:** `Available = Physical − Reserved`, причём
`Physical >= 0`, `Reserved >= 0`, `Reserved <= Physical`. Отрицательные остатки
невозможны — и на уровне бизнес-логики, и на уровне ограничений PostgreSQL.

Критические команды принимают заголовок **`Idempotency-Key`** — повторный запрос
с тем же ключом возвращает уже созданную сущность и не дублирует операцию.
"""

_TAGS_METADATA = [
    {"name": "products", "description": "Каталог товаров: SKU, названия, внешний ID Wildberries."},
    {
        "name": "warehouses",
        "description": "Склады фулфилмента (ФФ): создание, переименование, архивирование.",
    },
    {"name": "stocks", "description": "Складские остатки и товары в пути."},
    {
        "name": "operations",
        "description": "Складские операции: приход, резервы, перемещения, отправки, приёмка.",
    },
    {"name": "shipments", "description": "Отправки FBS/FBO."},
    {"name": "history", "description": "История операций и движений товара."},
    {"name": "wildberries", "description": "Интеграция с Wildberries (без токена — демо-режим)."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await dispose_engine()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Добавляет базовые security-заголовки к каждому ответу API."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Присваивает каждому запросу корреляционный id (X-Request-ID).

    Использует переданный клиентом `X-Request-ID` или генерирует UUID; возвращает
    его в заголовке ответа и в теле ошибки для трассировки.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def create_app() -> FastAPI:
    configure_logging(_settings.log_level)
    app = FastAPI(
        title=_settings.app_name,
        version="1.0.0",
        description=_DESCRIPTION,
        openapi_tags=_TAGS_METADATA,
        contact={"name": "CheckStock"},
        lifespan=lifespan,
    )

    origins = [o.strip() for o in _settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=_settings.api_prefix)

    @app.get("/healthz", tags=["health"], summary="Проверка состояния сервиса")
    async def healthz() -> dict:
        """Возвращает `{"status": "ok"}`, если приложение запущено."""
        return {"status": "ok"}

    @app.get("/health", tags=["health"], summary="Статус приложения и базы данных")
    async def health() -> dict:
        """Проверяет доступность PostgreSQL и возвращает статус сервиса."""
        database = "up"
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            database = "down"
        status = "ok" if database == "up" else "degraded"
        return {"status": status, "database": database, "version": "1.0.0"}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
