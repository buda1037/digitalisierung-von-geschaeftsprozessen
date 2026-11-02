"""Anwendungsstart und Verdrahtung der eigenständigen REST-Komponente."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .models import OrderRead
from .repository import ReturnRepository
from .routes import router
from .service import ReturnService

COMPONENT_ROOT = Path(__file__).resolve().parent.parent


def create_app(database_path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        configured_path = database_path or Path(
            os.getenv("REST_API_DB_PATH", "data/returns.sqlite3")
        )
        if not configured_path.is_absolute():
            configured_path = COMPONENT_ROOT / configured_path
        repository = ReturnRepository(configured_path)
        orders = json.loads((COMPONENT_ROOT / "mock-data" / "orders.json").read_text(encoding="utf-8"))
        repository.initialize([OrderRead.model_validate(order) for order in orders])
        application.state.return_service = ReturnService(repository)
        yield

    application = FastAPI(
        title="ShopEasy Retourenanmeldungen",
        description=(
            "Mock-Marktplatz-API zum Abruf von Retouren und Bestellungen sowie zur "
            "Aktualisierung des Retourenstatus. POST dient zum Anlegen von Mock-Retouren."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
