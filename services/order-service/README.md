# Order Service

Accepts orders via HTTP, persists them, and publishes `order.created` events.

## Events
| Direction | Event | Exchange / routing |
|-----------|-------|-------------------|
| Publishes | `order.created` | exchange `events` / `order.created` |

## HTTP API
- `POST /orders` — create a new order
- `GET /orders/{order_id}` — inspect an order

## Run locally (from the repo root)
uv run --package order-service uvicorn order_service.main:app --reload --port 8001 --reload-dir services/order-service/src --reload-dir shared/src

## Configuration
Environment variables (or `.env`): `RABBITMQ_URL`, `LOG_LEVEL`