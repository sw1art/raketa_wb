# CheckStock — Design Document

> Технический проект. Источник функциональных требований — `Task.md` (мастер-ТЗ) и `redirect (3).pdf`.
> Документ `redirect (2).pdf` (система снабжения «Ракета») использован только как бизнес-контекст и **не реализуется**.

## 1. Назначение

CheckStock — веб-приложение для управления складскими остатками товаров на складах фулфилмента (ФФ),
резервами под FBS, внутренними перемещениями и отправками FBS/FBO на Wildberries.

Ключевой принцип: **корректность складского учёта важнее количества функций.**

## 2. Архитектура

Clean Architecture + Modular Monolith + Event-Driven Architecture (один деплой, без микросервисов).

```
backend/src/
  domain/            # сущности, value objects, доменные сервисы, события, интерфейсы репозиториев
  application/       # use cases, commands, queries, обработчики событий, интерфейсы внешних зависимостей
  infrastructure/    # SQLAlchemy-модели, репозитории, session, outbox, RabbitMQ, WB-клиент
  presentation/      # FastAPI-роутеры, схемы, зависимости
  config/            # настройки (pydantic-settings)
```

Правила зависимостей:
- `domain` не знает ни о чём инфраструктурном (нет SQLAlchemy/HTTP/RabbitMQ).
- `application` зависит только от `domain` и интерфейсов.
- `infrastructure` реализует интерфейсы.
- `presentation` вызывает use cases; контроллеры тонкие.

## 3. Модель данных (PostgreSQL)

Все PK основных сущностей — `UUID`. Количество — `INTEGER` (неотрицательные, CHECK-ограничения).

| Таблица | Назначение |
|---|---|
| `stores` | магазин (справочник) |
| `products` | товар: `sku`, `name`, `wb_external_id`; `UNIQUE(store_id, sku)` |
| `warehouses` | ФФ: `name`, `is_active`, `archived_at` |
| `stocks` | остаток: `physical`, `reserved`; `UNIQUE(product_id, warehouse_id)`; CHECK `physical>=0`, `reserved>=0`, `reserved<=physical`; `version` (optimistic lock) |
| `stock_movements` | неизменяемый журнал движений (леджер) |
| `reservations` | резерв FBS: `status` ACTIVE/CANCELLED/SHIPPED |
| `transfers` / `transfer_items` | внутреннее перемещение + строки |
| `shipments` / `shipment_items` | отправка FBS/FBO + строки |
| `operations` / `operation_items` | история операций (аудит) + строки |
| `outbox_events` | transactional outbox |
| `processed_events` | дедупликация consumer (`UNIQUE(consumer_name, event_id)`) |
| `wb_sync_logs` | журнал синхронизаций WB |

`Available = Physical − Reserved` (вычисляемое, не хранится). Товар в пути **не входит** в `physical` —
он представлен строками `transfer_items`/`shipment_items` в статусе «в пути».

### Связи
- `stocks(product_id, warehouse_id)` — остаток SKU на ФФ.
- `reservations(product_id, warehouse_id)` — резерв на конкретном ФФ.
- `transfers(source, target)` — откуда/куда.
- `shipments(source_warehouse_id)` — откуда; `destination` — строка («Wildberries»/«Покупатель»); `external_status` — внешний статус WB.

## 4. Машины состояний

### Reservation (FBS)
```
ACTIVE ──cancel──▶ CANCELLED
ACTIVE ──ship────▶ SHIPPED
```
`CANCELLED` и `SHIPPED` терминальны.

### Transfer
```
DRAFT ──dispatch──▶ IN_TRANSIT ──receive──▶ RECEIVED
DRAFT ──cancel────▶ CANCELLED
```

### Shipment
```
FBS: DRAFT ──dispatch──▶ SHIPPED        (товар уехал к клиенту)
FBO: DRAFT ──dispatch──▶ IN_TRANSIT ──receive──▶ RECEIVED
     DRAFT ──cancel────▶ CANCELLED
```
Внешний статус WB хранится отдельно (`external_status`), внутренний — в `status`.

## 5. Транзакционность и конкурентный доступ

Каждая операция, меняющая баланс, выполняется в **одной транзакции PostgreSQL**:
1. `SELECT ... FOR UPDATE` по строке остатка (и по резерву/перемещению при необходимости);
2. проверка инвариантов (`available >= qty`, статусы);
3. изменение остатков;
4. запись `operation` + `operation_items` + `stock_movements`;
5. запись `outbox_events` в той же транзакции;
6. `COMMIT`.

Механизм блокировки: `SELECT FOR UPDATE` (сериализация конкурентных списаний одного SKU).
Дополнительно `version` для optimistic lock (используется там, где это удобно).

**Никаких сетевых вызовов (RabbitMQ/WB) внутри транзакции.** События публикуются только из Outbox.

## 6. Outbox + Event-Driven

`outbox_events`: `event_id`, `aggregate_type`, `aggregate_id`, `event_type`, `payload`, `status`
(PENDING/PUBLISHED/FAILED), `version`, `retry_count`, `last_error`, `next_retry_at`, `published_at`.

Publisher (фоновый процесс): выбирает PENDING через `FOR UPDATE SKIP LOCKED`, публикует в RabbitMQ
с **publisher confirms**, и только после подтверждения помечает PUBLISHED. При ошибке — backoff и retry,
после N попыток — FAILED.

RabbitMQ: durable topic exchange `checkstock.events`, durable queue, routing key = `event_type`,
manual ack, DLQ `checkstock.events.dlq`. События версионируются (`version`).

Consumer: `event-journal` (пишет события в `processed_events` — это и дедупликация, и журнал).
Идемпотентность через `UNIQUE(consumer_name, event_id)`.

## 7. Идемпотентность

Два уровня:
1. **Переход статусов.** `dispatch`/`receive` переводят статус условно (`WHERE status = 'DRAFT'` /
   проверка под блокировкой). Повторный вызов не меняет остатки — возвращается текущая сущность
   (идемпотентный no-op), двойного списания нет.
2. **Idempotency-Key.** Для критических команд (приход, резерв, создание перемещения/отправки) —
   опциональный заголовок `Idempotency-Key`; ключ уникален в `operations.idempotency_key`.
   Повторный запрос с тем же ключом возвращает уже созданную сущность.

## 8. Обработка нехватки

При нехватке операция отклоняется (остатки не меняются). Ответ содержит:
`requested`, `available` (на выбранном ФФ), `shortfall`, `other_warehouses` (доступные остатки SKU на
других ФФ) и предложение перемещения. Автоматического списания с другого ФФ нет.

## 9. Wildberries

Адаптер в `infrastructure/integrations/wildberries` (httpx, async). Токен — только из env
(`WB_API_TOKEN`). Таймауты, обработка HTTP/401, rate limiting, retry с exponential backoff,
`wb_sync_logs`. Без токена приложение работает в **демо-режиме** (внутренний учёт — источник истины,
WB не перезаписывает физические остатки). Точные endpoint'ы — из официальной документации
(https://dev.wildberries.ru/).

## 10. REST API

Префикс `/api/v1`. Единый формат ошибок, валидация, пагинация/сортировка/фильтры, OpenAPI. См. README.

## 11. Допущения

- `available` — вычисляемое поле (`physical - reserved`), не хранится.
- Товар в пути выводится из строк перемещений/отправок в статусе «в пути» (отдельной таблицы нет).
- Проверка доступности при *создании* перемещения/FBO — advisory; жёсткая проверка — при *отправке*
  (под блокировкой). Это гарантирует отсутствие отрицательных остатков при гонках.
- FBS-отправка создаётся и сразу отгружается в один шаг (из активного резерва).
- Логическое удаление ФФ — флаг `is_active=false`; история сохраняется; новый операции запрещены.
