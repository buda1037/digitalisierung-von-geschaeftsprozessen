"""Gemeinsames, marketplaceunabhängiges Datenformat der REST-Komponente."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class Marketplace(StrEnum):
    AMAZON = "amazon"
    ZALANDO = "zalando"


class ReturnStatus(StrEnum):
    NEW = "NEW"
    RECEIVED = "RECEIVED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


Reference = Annotated[str, Field(min_length=1, max_length=100)]


class Item(ApiModel):
    sku: Reference = Field(description="Artikelnummer des einzelnen retournierten Artikels")
    name: Annotated[str, Field(min_length=1, max_length=200)]


class ReturnCreate(ApiModel):
    marketplace: Marketplace
    order_id: Reference
    customer_reference: Reference
    item: Item = Field(description="Genau ein Artikel; eine Liste ist nicht zulässig")
    return_reason: Annotated[str, Field(min_length=1, max_length=1000)]
    registered_at: AwareDatetime = Field(
        description="Anmeldezeitpunkt beim Marketplace als ISO-8601-Zeitstempel mit Zeitzone"
    )

    @field_validator("marketplace", mode="before")
    @classmethod
    def normalize_marketplace(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("registered_at", mode="before")
    @classmethod
    def require_iso_datetime(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass
        raise ValueError("ISO-8601-Zeitstempel mit Zeitzone erforderlich")

    @field_validator("registered_at")
    @classmethod
    def validate_registration_time(cls, value: datetime) -> datetime:
        value = value.astimezone(UTC)
        if value > datetime.now(UTC):
            raise ValueError("Der Anmeldezeitpunkt darf nicht in der Zukunft liegen")
        return value


class ReturnRead(ReturnCreate):
    id: UUID = Field(description="Vom Mock erzeugte, systemübergreifend nutzbare Retouren-ID")
    received_at: AwareDatetime = Field(description="Erfassungszeitpunkt im Mock in UTC")
    status: ReturnStatus
    updated_at: AwareDatetime = Field(description="Zeitpunkt der letzten Statusänderung in UTC")


class ReturnStatusUpdate(ApiModel):
    status: ReturnStatus


class OrderItem(Item):
    quantity: Annotated[int, Field(strict=True, ge=1)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class OrderRead(ApiModel):
    order_id: Reference
    marketplace: Marketplace
    customer_reference: Reference
    ordered_at: AwareDatetime
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
    items: Annotated[list[OrderItem], Field(min_length=1)]


class ReturnPage(ApiModel):
    items: list[ReturnRead]
    total: int
    limit: int
    offset: int


class ErrorResponse(ApiModel):
    detail: str


class HealthResponse(ApiModel):
    status: str
