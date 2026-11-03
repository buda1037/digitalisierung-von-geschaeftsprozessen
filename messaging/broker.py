import logging
import os
from collections.abc import Callable

import pika

from events import ReturnStatusChanged

BROKER_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")

Handler = Callable[[ReturnStatusChanged], None]

log = logging.getLogger(__name__)


class Broker:
    def __init__(self, url: str = BROKER_URL, namespace: str = "retouren") -> None:
        self.namespace = namespace
        self.exchange = f"{namespace}.status"
        self.dead_letter = f"{namespace}.dead-letter"

        self.channel = pika.BlockingConnection(pika.URLParameters(url)).channel()
        self.channel.confirm_delivery()
        self.channel.exchange_declare(self.exchange, "topic", durable=True)
        self.channel.exchange_declare(self.dead_letter, "fanout", durable=True)
        self.channel.queue_declare(self.dead_letter, durable=True)
        self.channel.queue_bind(self.dead_letter, self.dead_letter)

    def close(self) -> None:
        self.channel.connection.close()

    def publish(self, event: ReturnStatusChanged) -> None:
        self.channel.basic_publish(
            self.exchange,
            event.status.routing_key,
            event.to_json(),
            pika.BasicProperties(
                content_type="application/json", delivery_mode=pika.DeliveryMode.Persistent
            ),
        )

    def subscribe(self, subscriber: str, routing_keys: list[str], handle: Handler) -> None:
        queue = self.declare_queue(subscriber, routing_keys)
        self.channel.basic_consume(
            queue,
            lambda _channel, method, _properties, body: self.handle_delivery(
                method.delivery_tag, body, handle
            ),
        )
        print(f"{subscriber} wartet auf Statusänderungen (Strg+C beendet)")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.close()

    def declare_queue(self, subscriber: str, routing_keys: list[str]) -> str:
        queue = f"{self.namespace}.{subscriber}"
        self.channel.queue_declare(
            queue, durable=True, arguments={"x-dead-letter-exchange": self.dead_letter}
        )
        for routing_key in routing_keys:
            self.channel.queue_bind(queue, self.exchange, routing_key)
        return queue

    def handle_delivery(self, delivery_tag: int, body: bytes, handle: Handler) -> None:
        try:
            handle(ReturnStatusChanged.from_json(body))
        except Exception:
            log.exception("Nachricht nicht verarbeitbar, sie wird in die Dead Letter Queue gelegt")
            self.channel.basic_reject(delivery_tag, requeue=False)
        else:
            self.channel.basic_ack(delivery_tag)
