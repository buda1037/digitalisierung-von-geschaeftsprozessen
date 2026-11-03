import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class ReturnStatus(StrEnum):
    NEW = "NEW"
    RECEIVED = "RECEIVED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"

    @property
    def routing_key(self) -> str:
        return f"retoure.status.{self.lower()}"


ANY_STATUS = "retoure.status.*"


class InvalidMessage(ValueError):
    pass


@dataclass(frozen=True)
class ReturnStatusChanged:
    return_id: str
    status: ReturnStatus
    source: str
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_json(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def from_json(cls, body: bytes) -> ReturnStatusChanged:
        try:
            data = json.loads(body)
            event = cls(
                return_id=data["return_id"],
                status=ReturnStatus(data["status"]),
                source=data["source"],
                event_id=data["event_id"],
                occurred_at=data["occurred_at"],
            )
            if datetime.fromisoformat(event.occurred_at).tzinfo is None:
                raise ValueError("occurred_at ohne Zeitzone")
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidMessage(repr(error)) from error
        return event
