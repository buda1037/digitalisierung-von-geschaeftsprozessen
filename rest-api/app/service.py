"""Verarbeitung einer validierten Anmeldung, unabhängig vom HTTP-Transport."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from .models import (
    Marketplace,
    OrderRead,
    ReturnCreate,
    ReturnPage,
    ReturnRead,
    ReturnStatus,
)
from .repository import ReturnRepository

ALLOWED_TRANSITIONS = {
    ReturnStatus.NEW: {ReturnStatus.RECEIVED},
    ReturnStatus.RECEIVED: {ReturnStatus.IN_REVIEW, ReturnStatus.APPROVED, ReturnStatus.REJECTED},
    ReturnStatus.IN_REVIEW: {ReturnStatus.APPROVED, ReturnStatus.REJECTED},
    ReturnStatus.APPROVED: {ReturnStatus.REFUNDED},
    ReturnStatus.REJECTED: set(),
    ReturnStatus.REFUNDED: set(),
}


class StatusConflict(ValueError):
    """Unzulässiger Übergang oder konkurrierende Statusänderung."""


class ReturnService:
    def __init__(self, repository: ReturnRepository) -> None:
        self.repository = repository

    def register(self, notification: ReturnCreate) -> ReturnRead:
        now = datetime.now(UTC)
        result = ReturnRead(
            **notification.model_dump(), id=uuid4(), received_at=now,
            status=ReturnStatus.NEW, updated_at=now,
        )
        return self.repository.add(result)

    def get(self, return_id: UUID) -> ReturnRead | None:
        return self.repository.get(return_id)

    def list(
        self, *, marketplace: Marketplace | None, order_id: str | None,
        limit: int, offset: int, status: ReturnStatus | None = None,
    ) -> ReturnPage:
        items, total = self.repository.list_returns(
            marketplace=marketplace, order_id=order_id, limit=limit, offset=offset, status=status,
        )
        return ReturnPage(items=items, total=total, limit=limit, offset=offset)

    def update_status(self, return_id: UUID, status: ReturnStatus) -> ReturnRead | None:
        notification = self.repository.get(return_id)
        if notification is None or notification.status == status:
            return notification
        if status not in ALLOWED_TRANSITIONS[notification.status]:
            raise StatusConflict(
                f"Statuswechsel von {notification.status.value} nach {status.value} ist nicht zulässig"
            )
        updated = self.repository.update_status(return_id, notification.status, status)
        if updated is None:
            raise StatusConflict("Status wurde zwischenzeitlich geändert; Retoure erneut abrufen")
        return updated

    def get_order(self, order_id: str) -> OrderRead | None:
        return self.repository.get_order(order_id)
