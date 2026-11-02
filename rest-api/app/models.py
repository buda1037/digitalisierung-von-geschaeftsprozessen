"""Gemeinsames, marketplaceunabhängiges Datenformat der REST-Komponente."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class Marketplace(StrEnum):
    AMAZON = "amazon"
    ZALANDO = "zalando"


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
    id: UUID = Field(description="Von ShopEasy erzeugte, systemübergreifend nutzbare Retouren-ID")
    received_at: AwareDatetime = Field(description="Eingangszeitpunkt bei ShopEasy in UTC")


class ReturnPage(ApiModel):
    items: list[ReturnRead]
    total: int
    limit: int
    offset: int


class ErrorResponse(ApiModel):
    detail: str


class HealthResponse(ApiModel):
    status: str
