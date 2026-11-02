"""Anwendungsstart und Verdrahtung der eigenständigen REST-Komponente."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

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
        repository.initialize()
        application.state.return_service = ReturnService(repository)
        yield

    application = FastAPI(
        title="ShopEasy Retourenanmeldungen",
        description=(
            "Mock-REST-API zum Empfang von Marketplace-Retourenanmeldungen. "
            "Jede Anmeldung enthält genau einen Artikel."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
