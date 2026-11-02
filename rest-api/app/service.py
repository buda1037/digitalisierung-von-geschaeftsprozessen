"""Verarbeitung einer validierten Anmeldung, unabhängig vom HTTP-Transport."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from .models import Marketplace, ReturnCreate, ReturnPage, ReturnRead
from .repository import ReturnRepository


class ReturnService:
    def __init__(self, repository: ReturnRepository) -> None:
        self.repository = repository

    def register(self, notification: ReturnCreate) -> ReturnRead:
        result = ReturnRead(
            **notification.model_dump(), id=uuid4(), received_at=datetime.now(UTC)
        )
        return self.repository.add(result)

    def get(self, return_id: UUID) -> ReturnRead | None:
        return self.repository.get(return_id)

    def list(
        self, *, marketplace: Marketplace | None, order_id: str | None,
        limit: int, offset: int,
    ) -> ReturnPage:
        items, total = self.repository.list(
            marketplace=marketplace, order_id=order_id, limit=limit, offset=offset
        )
        return ReturnPage(items=items, total=total, limit=limit, offset=offset)
