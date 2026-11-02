"""Lokale SQLite-Speicherung; keine Abhängigkeit von HTTP oder anderen Komponenten."""

import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator
from uuid import UUID

from .models import Marketplace, ReturnRead


class ReturnRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        # Eine Verbindung je Operation, damit die synchronen HTTP-Endpunkte
        # unabhängig voneinander im FastAPI-Threadpool arbeiten können.
        with closing(sqlite3.connect(self.database_path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                yield connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS return_notifications (
                    id TEXT PRIMARY KEY,
                    marketplace TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    customer_reference TEXT NOT NULL,
                    item_sku TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    return_reason TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    received_at TEXT NOT NULL
                )"""
            )

    def add(self, notification: ReturnRead) -> ReturnRead:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO return_notifications
                (id, marketplace, order_id, customer_reference, item_sku,
                 item_name, return_reason, registered_at, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(notification.id),
                    notification.marketplace.value,
                    notification.order_id,
                    notification.customer_reference,
                    notification.item.sku,
                    notification.item.name,
                    notification.return_reason,
                    notification.registered_at.isoformat(),
                    notification.received_at.isoformat(),
                ),
            )
        return notification

    def get(self, return_id: UUID) -> ReturnRead | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM return_notifications WHERE id = ?", (str(return_id),)
            ).fetchone()
        return self._to_model(row) if row else None

    def list(
        self, *, marketplace: Marketplace | None, order_id: str | None,
        limit: int, offset: int,
    ) -> tuple[list[ReturnRead], int]:
        clauses: list[str] = []
        parameters: list[str] = []
        if marketplace is not None:
            clauses.append("marketplace = ?")
            parameters.append(marketplace.value)
        if order_id is not None:
            clauses.append("order_id = ?")
            parameters.append(order_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connection() as connection:
            # Count und Seite stammen aus demselben SQLite-Lesesnapshot.
            connection.execute("BEGIN")
            total = connection.execute(
                "SELECT COUNT(*) FROM return_notifications" + where, parameters
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM return_notifications" + where
                + " ORDER BY received_at DESC, id DESC LIMIT ? OFFSET ?",
                [*parameters, limit, offset],
            ).fetchall()
        return [self._to_model(row) for row in rows], total

    @staticmethod
    def _to_model(row: sqlite3.Row) -> ReturnRead:
        return ReturnRead.model_validate({
            "id": row["id"],
            "marketplace": row["marketplace"],
            "order_id": row["order_id"],
            "customer_reference": row["customer_reference"],
            "item": {"sku": row["item_sku"], "name": row["item_name"]},
            "return_reason": row["return_reason"],
            "registered_at": row["registered_at"],
            "received_at": row["received_at"],
        })
