import time
from uuid import uuid4

from broker import Broker
from events import ReturnStatus, ReturnStatusChanged

SCENARIOS = {
    "Amazon-Retoure, angenommen und erstattet": [
        ReturnStatus.NEW,
        ReturnStatus.RECEIVED,
        ReturnStatus.APPROVED,
        ReturnStatus.REFUNDED,
    ],
    "Zalando-Retoure, Grenzfall manuell abgelehnt": [
        ReturnStatus.NEW,
        ReturnStatus.RECEIVED,
        ReturnStatus.IN_REVIEW,
        ReturnStatus.REJECTED,
    ],
}

SECONDS_BETWEEN_STATUS_CHANGES = 0.5


def main() -> None:
    broker = Broker()
    for title, statuses in SCENARIOS.items():
        return_id = str(uuid4())
        print(f"\n{title} ({return_id})")
        for status in statuses:
            broker.publish(ReturnStatusChanged(return_id, status, source="simulator"))
            print(f"  {status.routing_key}")
            time.sleep(SECONDS_BETWEEN_STATUS_CHANGES)
    broker.close()


if __name__ == "__main__":
    main()
