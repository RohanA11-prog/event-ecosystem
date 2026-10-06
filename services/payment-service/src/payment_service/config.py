from ecosystem_shared import ServiceSettings

QUEUE_ORDER_CREATED = "payment-service.order-created"


class PaymentSettings(ServiceSettings):
    service_name: str = "payment-service"
