# Notification Service

Consumes `payment.processed` and `payment.failed` events, and simulates sending a notification (email/SMS) to the customer.

## Events
| Direction | Event | Queue / routing |
|-----------|-------|-----------------|
| Consumes | `payment.processed`, `payment.failed` | queue `notification-service.payment-events` / exchange `events` |

## HTTP API
- `GET /notifications` — list all notifications sent
- `GET /notifications/{order_id}` — get the notification for a specific order

## Run locally (from the repo root)
uv run --package notification-service uvicorn notification_service.main:app --reload --port 8003 --reload-dir services/notification-service/src --reload-dir shared/src

## Configuration
Environment variables (or `.env`): `RABBITMQ_URL`, `LOG_LEVEL`

## Test hooks (simulation)
`cust-notify-fail` makes the notification sender fail, so you can test failure isolation.