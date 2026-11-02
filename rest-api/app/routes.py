"""HTTP-Schnittstelle der REST-Komponente, versioniert unter /api/v1."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from .models import (
    ErrorResponse, HealthResponse, Marketplace, ReturnCreate, ReturnPage, ReturnRead,
)
from .service import ReturnService

router = APIRouter()


def get_return_service(request: Request) -> ReturnService:
    return request.app.state.return_service


Service = Annotated[ReturnService, Depends(get_return_service)]


@router.get("/health", tags=["Betrieb"], response_model=HealthResponse)
def health() -> HealthResponse:
    """Zeigt an, dass die Anwendung gestartet und erreichbar ist (Liveness)."""
    return HealthResponse(status="ok")


@router.post(
    "/api/v1/returns", tags=["Retourenanmeldungen"],
    response_model=ReturnRead, status_code=status.HTTP_201_CREATED,
    summary="Retourenanmeldung eines Marketplaces entgegennehmen",
)
def register_return(
    notification: ReturnCreate, response: Response, request: Request, service: Service,
) -> ReturnRead:
    result = service.register(notification)
    response.headers["Location"] = str(
        request.url_for("get_return", return_id=str(result.id))
    )
    return result


@router.get(
    "/api/v1/returns", tags=["Retourenanmeldungen"], response_model=ReturnPage,
    summary="Retourenanmeldungen auflisten und filtern",
)
def list_returns(
    service: Service,
    marketplace: Marketplace | None = None,
    order_id: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReturnPage:
    return service.list(
        marketplace=marketplace, order_id=order_id, limit=limit, offset=offset
    )


@router.get(
    "/api/v1/returns/{return_id}", tags=["Retourenanmeldungen"],
    response_model=ReturnRead,
    responses={404: {"model": ErrorResponse, "description": "Retoure nicht gefunden"}},
    summary="Eine Retourenanmeldung anhand ihrer UUID abrufen",
)
def get_return(return_id: UUID, service: Service) -> ReturnRead:
    notification = service.get(return_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Retourenanmeldung nicht gefunden")
    return notification
