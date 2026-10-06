"""Names shared by every service. Change these in one place only."""

EXCHANGE_NAME = "events"

# Routing keys double as event types.
ORDER_CREATED = "order.created"
PAYMENT_PROCESSED = "payment.processed"
PAYMENT_FAILED = "payment.failed"
