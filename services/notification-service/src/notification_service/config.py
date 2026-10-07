from ecosystem_shared import ServiceSettings

QUEUE_PAYMENT_EVENTS = "notification-service.payment-events"


class NotificationSettings(ServiceSettings):
    service_name: str = "notification-service"
