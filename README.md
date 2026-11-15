# CheckStock

Веб-приложение для управления складскими остатками товаров на складах фулфилмента (ФФ),
резервами под FBS и отправками FBS/FBO на маркетплейс Wildberries.

CheckStock отвечает на вопрос **«где сейчас товар и сколько его доступно»**: менеджер сразу видит
физический остаток, резерв FBS, доступное количество и товары в пути (между ФФ, на WB по FBO, к
клиенту по FBS) по каждому артикулу и каждому складу.

Главный принцип проекта — **корректность складского учёта**: невозможны отрицательные остатки,
двойное списание, рассинхрон «остаток изменился, но операция не записана».

---

## 1. Технологический стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, Pydantic 2 |
| Messaging | RabbitMQ, aio-pika, Transactional Outbox |
| Frontend | Nuxt 3, Vue 3, TypeScript, Composition API, `$fetch` |
| Infra | Docker, Docker Compose, PostgreSQL 16, RabbitMQ 3.13 |
| Integration | Wildberries API (httpx) |
| Tests | pytest, pytest-asyncio |

---

## 2. Архитектура

**Clean Architecture + Modular Monolith + Event-Driven Architecture** (один деплой, без микросервисов).

```
backend/src/
  domain/            # сущности, value objects, доменные сервисы, события, интерфейсы репозиториев
  application/       # use cases, commands, queries, обработчики событий, интерфейсы внешних зависимостей
  infrastructure/    # SQLAlchemy-модели, репозитории, session, outbox, RabbitMQ, WB-клиент
  presentation/      # FastAPI-роутеры, схемы, зависимости
  config/            # настройки
```

- `domain` не зависит от FastAPI/SQLAlchemy/PostgreSQL/RabbitMQ/HTTP — только чистый Python
  (проверяется unit-тестами без БД).
- `application` содержит по одному use case на каждый бизнес-сценарий и явную границу транзакции.
- `infrastructure` реализует порты (репозитории, outbox, RabbitMQ, WB).
- `presentation` — тонкие контроллеры: приняли запрос → вызвали use case → вернули результат.

### Transactional Outbox + EDA

Каждая складская операция в **одной транзакции PostgreSQL**:
1. изменяет остатки (`SELECT ... FOR UPDATE`),
2. создаёт запись операции и движения товара,
3. кладёт `OutboxEvent` в таблицу `outbox_events`.

Отдельный процесс `outbox-worker` публикует события в RabbitMQ (с publisher confirms) и помечает их
`PUBLISHED`. Событие **никогда** не публикуется до подтверждения брокера. RabbitMQ — только
распространение событий; **источником истины остатков остаётся PostgreSQL**.

События: `StockReceived`, `StockReserved`, `StockReservationCancelled`, `FBSOrderShipped`,
`FBOShipmentDispatched`, `FBOShipmentReceived`, `TransferDispatched`, `TransferReceived`,
`WarehouseArchived`.

---

## 3. Модель данных

Все PK основных сущностей — `UUID`. Количество — `INTEGER` с CHECK-ограничениями.

| Таблица | Назначение |
|---|---|
| `stores` | магазин (справочник) |
| `products` | товар: `sku`, `name`, `wb_external_id`; `UNIQUE(store_id, sku)` |
| `warehouses` | ФФ: `name`, `is_active`, `archived_at` |
| `stocks` | остаток: `physical`, `reserved`, `version`; `UNIQUE(product_id, warehouse_id)`; CHECK `physical>=0`, `reserved>=0`, `reserved<=physical` |
| `stock_movements` | неизменяемый журнал движений (леджер для сверки) |
| `reservations` | резерв FBS: `status` ACTIVE/CANCELLED/SHIPPED |
| `transfers` / `transfer_items` | внутреннее перемещение + строки |
| `shipments` / `shipment_items` | отправка FBS/FBO + строки; `external_status` — внешний статус WB |
| `operations` / `operation_items` | история операций (аудит) + строки |
| `outbox_events` | transactional outbox |
| `processed_events` | дедупликация consumer: `UNIQUE(consumer_name, event_id)` |
| `wb_sync_logs` | журнал синхронизаций WB |

## 4. Бизнес-логика

- **Остатки**: `Available = Physical − Reserved`. Инварианты: `Physical >= 0`, `Reserved >= 0`,
  `Reserved <= Physical`, `Available >= 0` (гарантируются и в коде, и CHECK-ограничениями БД).
- **Резерв FBS**: увеличивает `Reserved`, не меняет `Physical`. Отмена — освобождает резерв.
- **Отправка FBS**: из активного резерва — уменьшает `Physical` и `Reserved` одновременно.
- **Перемещение**: два этапа — `dispatch` (уменьшает `Physical` источника, товар «в пути») и
  `receive` (увеличивает `Physical` целевого ФФ). Повторная приёмка невозможна.
- **FBO**: `dispatch` уменьшает `Physical` ФФ (товар «в пути» на WB), `receive` фиксирует приёмку на
  WB (физический остаток ФФ больше не меняется).
- **Товар в пути** не входит в `physical` — он выводится из строк перемещений/отправок в статусе
  «в пути» (`transfers.status=IN_TRANSIT`, `shipments` FBO `IN_TRANSIT` / FBS `SHIPPED`).

### Машины состояний

```
Reservation: ACTIVE → CANCELLED | SHIPPED
Transfer:    DRAFT → IN_TRANSIT → RECEIVED  (DRAFT → CANCELLED)
Shipment FBS: DRAFT → SHIPPED
Shipment FBO: DRAFT → IN_TRANSIT → RECEIVED  (DRAFT → CANCELLED)
```

---

## 5. Запуск

### Требования
- Docker и Docker Compose (проверено на Docker Engine 29+).

### Шаги

```bash
# 1. Клонировать репозиторий
git clone <repo-url> checkstock && cd checkstock

# 2. Настроить окружение (необязательно — есть дефолты)
cp .env.example .env
#   WB_API_TOKEN оставьте пустым для локального демо-режима

# 3. Собрать и запустить
docker compose up --build -d

# 4. Проверить статус
docker compose ps
```

После запуска:
- **Frontend**: http://localhost:3000
- **Backend API / Swagger**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672 (логин/пароль `checkstock`/`checkstock` по умолчанию)

При старте `backend` автоматически применяет миграции Alembic и идемпотентно заполняет тестовые
данные (магазин «Ракета», ФФ «Север» и «Юг», товары SKU-101/102/103 и начальные остатки).

### Остановка

```bash
docker compose down            # сохраняет данные (volumes)
docker compose down -v         # полностью удаляет данные
```

---

## 6. Тестовые данные

| SKU | Товар | Север | Юг |
|---|---|---|---|
| SKU-101 | Органайзер | 10 | 6 |
| SKU-102 | Контейнер | 5 | 0 |
| SKU-103 | Корзина | 0 | 4 |

---

## 7. Тестирование

```bash
# Backend: установить зависимости
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e ".[dev]"

# Unit-тесты (домен, без БД)
pytest tests/unit

# Интеграционные тесты (нужен реальный PostgreSQL)
export TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:5433/checkstock_test
pytest tests/integration

# Все тесты
pytest
```

Интеграционные тесты покрывают обязательные сценарии: приход, резерв, отмена резерва, FBS,
перемещение, FBO, нехватка, архивирование ФФ с остатком, повторное подтверждение, конкурентные
списания, поведение Outbox при недоступном RabbitMQ.

---

## 8. Примеры API

Базовый префикс `/api/v1`. Единый формат ошибок:

```json
{"error": {"code": "stock_shortage", "message": "...", "detail": {...}}}
```

```bash
# Остатки
curl http://localhost:8000/api/v1/stocks?sku=SKU-101

# Приход 5 единиц
curl -X POST http://localhost:8000/api/v1/operations/receipts \
  -H "Content-Type: application/json" -H "Idempotency-Key: rec-1" \
  -d '{"warehouse_id": "<uuid>", "product_id": "<uuid>", "quantity": 5}'

# Резерв FBS
curl -X POST http://localhost:8000/api/v1/operations/reservations \
  -H "Content-Type: application/json" \
  -d '{"warehouse_id": "<uuid>", "product_id": "<uuid>", "quantity": 3}'

# Перемещение: создать → отправить → принять
curl -X POST http://localhost:8000/api/v1/operations/transfers \
  -H "Content-Type: application/json" \
  -d '{"source_warehouse_id":"<uuid>","target_warehouse_id":"<uuid>","items":[{"product_id":"<uuid>","quantity":4}]}'
curl -X POST http://localhost:8000/api/v1/operations/transfers/<id>/dispatch
curl -X POST http://localhost:8000/api/v1/operations/transfers/<id>/receive

# Отправка FBO
curl -X POST http://localhost:8000/api/v1/operations/shipments/fbo \
  -H "Content-Type: application/json" \
  -d '{"source_warehouse_id":"<uuid>","items":[{"product_id":"<uuid>","quantity":4}]}'
```

Полный контракт — в Swagger: http://localhost:8000/docs.

---

## 9. Архитектурные решения

### Зачем Clean Architecture
Складская логика — это чистая функция над остатками; она не должна зависеть от ORM, HTTP или
брокера. Разделение слоёв позволяет тестировать домен без БД и менять инфраструктуру, не трогая
правила учёта.

### Зачем Outbox
Чтобы «остаток изменился» и «событие опубликовано» были атомарны. Событие пишется в ту же
транзакцию, что и остаток, а публикуется фоновым процессом — поэтому невозможна потеря события и не
нужен сетевой вызов к RabbitMQ внутри транзакции изменения остатков.

### Почему PostgreSQL — источник истины
Все инварианты (неотрицательность, `reserved <= physical`, уникальность) продублированы на уровне
БД. RabbitMQ и Wildberries — только каналы распространения/интеграции, они никогда не перезаписывают
физические остатки.

### Идемпотентность
1. **Переходы статусов.** `dispatch`/`receive` меняют статус условно (под блокировкой). Повторный
   вызов — no-op: остаток не списывается повторно.
2. **Idempotency-Key.** Критические команды принимают заголовок `Idempotency-Key`; ключ уникален в
   `operations.idempotency_key`, повторный запрос возвращает уже созданную сущность.

### Как предотвращаются гонки
Каждая операция блокирует строку остатка через `SELECT ... FOR UPDATE`. Два параллельных списания
сериализуются: вторая операция видит актуальный остаток и отклоняется при нехватке (см. сценарий
конкурентных операций в тестах). Дополнительно есть `version` для optimistic lock.

### Как учитываются товары в пути
Товар в пути — это строки `transfer_items`/`shipment_items` в статусе «в пути». Он не входит в
`physical` ФФ и считается отдельно (`GET /api/v1/stocks/in-transit`).

### Как интегрируется Wildberries
Адаптер `WildberriesClient` изолирован в `infrastructure`. Токен берётся только из `WB_API_TOKEN`
(env); есть таймауты, rate limiting, retry с exponential backoff, журнал `wb_sync_logs`. Без токена
приложение работает в **демо-режиме** и ничего не «придумывает»: внутренний учёт остаётся источником
истины, внешние данные WB не перезаписывают физические остатки.

---

## 10. Структура репозитория

```
.
├── backend/            # FastAPI + SQLAlchemy + Alembic + тесты
│   ├── src/{domain,application,infrastructure,presentation,config}
│   ├── migrations/     # Alembic
│   └── tests/{unit,integration}
├── frontend/           # Nuxt 3
├── docker-compose.yml
├── DESIGN.md           # проектная документация (ER, состояния, допущения)
└── README.md
```
