# Event-Driven Microservices Ecosystem (Python)

An asynchronous order-processing system built with **Python, FastAPI and RabbitMQ**, where independent services collaborate **only through a message broker**, never by calling each other over HTTP.

> **Status: 🚧 In-progress portfolio project.** Phases 0–5 are complete: broker, shared event contracts, and the Order, Payment and Notification services. In progress: API Gateway, full Docker Compose orchestration, observability, dead-letter queues and end-to-end tests.

## Architecture

```
 Client ──HTTP──▶ ┌───────────────┐
                  │ Order Service │ :8001
                  └───────┬───────┘
                          │ publishes order.created
                          ▼
 ╔═══════════════════════════════════════════════════════╗
 ║          RabbitMQ  ·  topic exchange "events"         ║
 ╚═══════════════╤═══════════════════════════╤═══════════╝
                 │ order.created             │ payment.processed
                 ▼                           │ payment.failed
        ┌─────────────────┐                  ▼
        │ Payment Service │ :8002   ┌──────────────────────┐
        └────────┬────────┘         │ Notification Service │ :8003
                 │                  └──────────────────────┘
                 │ publishes payment.processed / payment.failed
                 └──────▶ back to the broker
```

| Service | Role | Consumes | Publishes |
|---|---|---|---|
| **Order Service** | Owns the order lifecycle, exposes the REST API | – | `order.created` |
| **Payment Service** | Simulates charging the customer | `order.created` | `payment.processed`, `payment.failed` |
| **Notification Service** | Sends (simulated) customer notifications | `payment.processed`, `payment.failed` | – |
| **RabbitMQ** | Asynchronous backbone (topic exchange, durable queues) | | |

Each consumer owns its **own queue**, so a slow or failing service never blocks the others.

## Tech stack

- **Python 3.13**, `asyncio` end to end
- **FastAPI** + **Uvicorn** for the HTTP APIs
- **RabbitMQ** with **aio-pika** for messaging
- **Pydantic v2** + **pydantic-settings** for event contracts and typed configuration
- **uv** workspace (one lockfile, one shared package, one virtualenv)
- **pytest**, **pytest-asyncio**, **httpx** for testing
- **Ruff**, **Black**, **mypy (strict)** for code quality
- **Docker Compose** for the broker (full service orchestration coming)

## Key concepts implemented

- ✅ **Event-driven decoupling:** services communicate only via events on a topic exchange
- ✅ **Typed event contracts:** shared Pydantic models with `event_id`, `correlation_id` and schema version
- ✅ **Idempotent consumers:** dedup on `event_id`, plus deterministic output ids (`uuid5`) so reprocessing is harmless
- ✅ **Retries with exponential backoff** for transient failures, with reject-without-requeue for poison messages
- ✅ **At-least-once delivery handling:** manual acks, durable queues, persistent messages, publisher confirms
- ✅ **Failure isolation:** a failing Notification Service cannot block or undo a payment; downstream outages are absorbed by queues
- ✅ **Correlation ids** tying one order's whole flow together across services
- ✅ **Safe publish handling:** timeouts and rollback if the broker is down; automatic reconnection
- ✅ **Money as `Decimal`**, never floats
- 🔜 Dead-letter queues, durable dedup, API Gateway, health/readiness endpoints, structured logging, end-to-end tests

## Run locally (Windows / PowerShell)

**Prerequisites:** Python 3.13, [uv](https://docs.astral.sh/uv/), Docker Desktop, Git.

```powershell
git clone https://github.com/RohanA11-prog/event-ecosystem.git
cd event-ecosystem
Copy-Item .env.example .env
uv sync
docker compose up -d          # starts RabbitMQ (UI: http://localhost:15672, guest / guest)
```

Then start each service in its own terminal, from the repo root:

```powershell
uv run --package notification-service uvicorn notification_service.main:app --reload --port 8003 --reload-dir services/notification-service/src --reload-dir shared/src
uv run --package payment-service uvicorn payment_service.main:app --reload --port 8002 --reload-dir services/payment-service/src --reload-dir shared/src
uv run --package order-service uvicorn order_service.main:app --reload --port 8001 --reload-dir services/order-service/src --reload-dir shared/src
```

Create an order (or use `requests/order-service.http` with the VS Code REST Client extension):

```powershell
curl.exe -X POST http://localhost:8001/orders -H "Content-Type: application/json" -d '{\"customer_id\":\"cust-1\",\"items\":[{\"sku\":\"ABC\",\"quantity\":2,\"unit_price\":\"10.50\"}]}'
```

Then inspect the results: `GET :8002/payments/{order_id}` and `GET :8003/notifications`. Interactive API docs are at `/docs` on each service.

### Simulation hooks (to see the resilience patterns)

| `customer_id` | Behaviour |
|---|---|
| `cust-declined` | Payment declined, `payment.failed` is published |
| `cust-flaky` | Payment gateway fails twice, retries with backoff, then succeeds |
| `cust-notify-fail` | Payment succeeds but notification always fails; the payment is unaffected |
| any, total over 1000 | Payment declined for exceeding the limit |

## Tests and code quality

```powershell
uv run pytest                 # 24 tests
uv run ruff check .
uv run black --check .
uv run mypy shared/src services/order-service/src services/payment-service/src services/notification-service/src
```

## Repository layout

```
shared/                      Event contracts, settings, broker client, reusable consumer
services/order-service/      REST API + event producer
services/payment-service/    Event consumer + producer
services/notification-service/  Event consumer
tests/                       Unit and API tests (fakes replace the broker)
requests/                    .http files for manual API testing
docker-compose.yml           RabbitMQ on the named network "event-net"
```

## Roadmap

1. API Gateway
2. Docker Compose for all services (`docker compose up --build`)
3. Observability: structured logging (structlog), `/health` and `/ready`, optional OpenTelemetry
4. Resilience: dead-letter queues, durable idempotency, documented failure modes
5. End-to-end tests covering order → payment → notification and service recovery