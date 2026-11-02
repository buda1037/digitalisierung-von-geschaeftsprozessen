"""Lokale SQLite-Speicherung; keine Abhängigkeit von HTTP oder anderen Komponenten."""

import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from .models import Marketplace, OrderRead, ReturnRead, ReturnStatus


class ReturnRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection]:
        # Eine Verbindung je Operation, damit die synchronen HTTP-Endpunkte
        # unabhängig voneinander im FastAPI-Threadpool arbeiten können.
        with closing(sqlite3.connect(self.database_path, timeout=5)) as connection:
            connection.row_factory = sqlite3.Row
            with connection:
                yield connection

    def initialize(self, orders: list[OrderRead] | None = None) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
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
                    received_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    updated_at TEXT NOT NULL
                )"""
            )
            # Vorhandene Sprint-2-Datenbanken ohne Status verlustfrei erweitern.
            columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(return_notifications)")
            }
            if "status" not in columns:
                connection.execute(
                    "ALTER TABLE return_notifications ADD COLUMN status TEXT NOT NULL DEFAULT 'NEW'"
                )
            if "updated_at" not in columns:
                connection.execute(
                    "ALTER TABLE return_notifications ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''"
                )
                connection.execute("UPDATE return_notifications SET updated_at = received_at")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS mock_orders (order_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )
            connection.executemany(
                "INSERT INTO mock_orders (order_id, payload) VALUES (?, ?) "
                "ON CONFLICT(order_id) DO NOTHING",
                [(order.order_id, order.model_dump_json()) for order in orders or []],
            )

    def add(self, notification: ReturnRead) -> ReturnRead:
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO return_notifications
                (id, marketplace, order_id, customer_reference, item_sku,
                 item_name, return_reason, registered_at, received_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    notification.status.value,
                    notification.updated_at.isoformat(),
                ),
            )
        return notification

    def get(self, return_id: UUID) -> ReturnRead | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM return_notifications WHERE id = ?", (str(return_id),)
            ).fetchone()
        return self._to_model(row) if row else None

    def list_returns(
        self, *, marketplace: Marketplace | None, order_id: str | None,
        limit: int, offset: int, status: ReturnStatus | None = None,
    ) -> tuple[list[ReturnRead], int]:
        clauses: list[str] = []
        parameters: list[str] = []
        if marketplace is not None:
            clauses.append("marketplace = ?")
            parameters.append(marketplace.value)
        if order_id is not None:
            clauses.append("order_id = ?")
            parameters.append(order_id)
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status.value)
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

    def update_status(
        self, return_id: UUID, previous_status: ReturnStatus, status: ReturnStatus,
    ) -> ReturnRead | None:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE return_notifications SET status = ?, updated_at = ? "
                "WHERE id = ? AND status = ?",
                (status.value, datetime.now(UTC).isoformat(), str(return_id), previous_status.value),
            )
            if cursor.rowcount != 1:
                return None
            row = connection.execute(
                "SELECT * FROM return_notifications WHERE id = ?", (str(return_id),)
            ).fetchone()
        return self._to_model(row)

    def get_order(self, order_id: str) -> OrderRead | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT payload FROM mock_orders WHERE order_id = ?", (order_id,)
            ).fetchone()
        return OrderRead.model_validate_json(row["payload"]) if row else None

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
            "status": row["status"],
            "updated_at": row["updated_at"],
        })
