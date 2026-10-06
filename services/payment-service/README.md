# Payment Service

Consumes `order.created`, simulates a payment, and publishes `payment.processed` or `payment.failed`.

## Events
| Direction | Event | Queue / routing |
|---|---|---|
| Consumes | `order.created` | queue `payment-service.order-created` |
| Publishes | `payment.processed`, `payment.failed` | exchange `events` |

## HTTP API
- `GET /payments/{order_id}` — inspect the payment for an order

## Run locally (from the repo root)
    uv run --package payment-service uvicorn payment_service.main:app --reload --port 8002

## Configuration
Environment variables (or `.env`): `RABBITMQ_URL`, `LOG_LEVEL`

## Test hooks (simulation)
`cust-declined` is declined, `cust-flaky` fails twice then succeeds, totals over 1000 are declined.