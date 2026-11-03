import time
from uuid import uuid4

import pika
import pytest

from broker import Broker
from events import ANY_STATUS, ReturnStatus, ReturnStatusChanged


@pytest.fixture
def broker():
    try:
        broker = Broker(namespace=f"test-{uuid4()}")
    except pika.exceptions.AMQPConnectionError:
        pytest.skip("RabbitMQ nicht erreichbar, zuerst docker compose up -d")
    yield broker
    for subscriber in ("kundenbenachrichtigung", "prozesslog"):
        broker.channel.queue_delete(f"{broker.namespace}.{subscriber}")
    broker.channel.queue_delete(broker.dead_letter)
    broker.channel.exchange_delete(broker.exchange)
    broker.channel.exchange_delete(broker.dead_letter)
    broker.close()


def received(broker, queue, timeout=2.0):
    bodies, deadline = [], time.monotonic() + timeout
    while time.monotonic() < deadline:
        method, _properties, body = broker.channel.basic_get(queue, auto_ack=True)
        if method:
            bodies.append(body)
        elif bodies:
            break
        else:
            time.sleep(0.05)
    return bodies


def statuses(bodies):
    return [ReturnStatusChanged.from_json(body).status for body in bodies]


def test_abonnenten_erhalten_nur_die_abonnierten_status(broker):
    customer = broker.declare_queue("kundenbenachrichtigung", [ReturnStatus.NEW.routing_key])
    process_log = broker.declare_queue("prozesslog", [ANY_STATUS])

    for status in (ReturnStatus.NEW, ReturnStatus.IN_REVIEW):
        broker.publish(ReturnStatusChanged("RET-1", status, source="test"))

    assert statuses(received(broker, customer)) == [ReturnStatus.NEW]
    assert statuses(received(broker, process_log)) == [ReturnStatus.NEW, ReturnStatus.IN_REVIEW]


def fail(_event):
    raise RuntimeError("Datenbank nicht erreichbar")


@pytest.mark.parametrize(
    ("body", "handle"),
    [
        (b"kein JSON", lambda _event: None),
        (ReturnStatusChanged("RET-1", ReturnStatus.NEW, source="test").to_json(), fail),
    ],
    ids=["ungueltige-nachricht", "verarbeitungsfehler"],
)
def test_nicht_verarbeitbare_nachricht_landet_in_der_dead_letter_queue(broker, body, handle):
    queue = broker.declare_queue("prozesslog", [ANY_STATUS])
    broker.channel.basic_publish(broker.exchange, ReturnStatus.NEW.routing_key, body)

    method, _properties, delivered = broker.channel.basic_get(queue)
    broker.handle_delivery(method.delivery_tag, delivered, handle)

    assert received(broker, broker.dead_letter) == [body]
    assert broker.channel.basic_get(queue)[0] is None
