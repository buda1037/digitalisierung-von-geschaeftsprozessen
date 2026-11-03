"""Integrationstests über echtes HTTP, mit isolierten temporären Datenbanken."""

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import uvicorn
from app.main import COMPONENT_ROOT, create_app
from app.models import ReturnStatus
from app.repository import ReturnRepository


class LocalAPI:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.server = None
        self.thread = None
        self.listener = None

    def start(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.base_url = f"http://127.0.0.1:{self.listener.getsockname()[1]}"
        self.server = uvicorn.Server(uvicorn.Config(
            create_app(self.database_path), log_level="error", lifespan="on",
        ))
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [self.listener]}, daemon=True,
        )
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() >= deadline:
                self.stop()
                raise RuntimeError("Testserver konnte nicht gestartet werden")
            time.sleep(0.01)

    def stop(self):
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise RuntimeError("Testserver konnte nicht beendet werden")
        if self.listener:
            self.listener.close()

    def call(self, method, path, payload=None):
        request = Request(
            self.base_url + path, method=method,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read()), response.headers


class APITests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="shopeasy-test-")
        self.addCleanup(temporary.cleanup)
        self.database = Path(temporary.name) / "returns.sqlite3"
        self.api = LocalAPI(self.database)
        self.addCleanup(self.api.stop)
        self.api.start()

    def create(self, marketplace="amazon", order_id=None):
        payload = json.loads((COMPONENT_ROOT / "mock-data" / f"{marketplace}-return.json").read_text(encoding="utf-8"))
        if order_id is not None:
            payload["order_id"] = order_id
        code, body, headers = self.api.call("POST", "/api/v1/returns", payload)
        self.assertEqual(code, 201, body)
        self.assertEqual(headers["Location"], self.api.base_url + "/api/v1/returns/" + body["id"])
        return body

    def change(self, notification, status, expected=200):
        code, body, _ = self.api.call(
            "PATCH", f"/api/v1/returns/{notification['id']}/status", {"status": status},
        )
        self.assertEqual(code, expected, body)
        return body

    def test_orders_exist_without_returns(self):
        for order_id, marketplace, item_count in (
            ("AMZ-2026-10001", "amazon", 2), ("ZAL-2026-20002", "zalando", 1),
        ):
            with self.subTest(order=order_id):
                code, order, _ = self.api.call("GET", "/api/v1/orders/" + order_id)
                self.assertEqual(code, 200)
                self.assertEqual(order["order_id"], order_id)
                self.assertEqual(order["marketplace"], marketplace)
                self.assertEqual(len(order["items"]), item_count)
                self.assertIn("quantity", order["items"][0])
                self.assertIn("unit_price", order["items"][0])
                self.assertEqual(order["currency"], "EUR")
        self.assertEqual(self.api.call("GET", "/api/v1/returns")[1]["total"], 0)

    def test_create_and_get_return(self):
        notification = self.create()
        self.assertEqual(notification["status"], "NEW")
        self.assertEqual(notification["received_at"], notification["updated_at"])
        code, fetched, _ = self.api.call("GET", "/api/v1/returns/" + notification["id"])
        self.assertEqual(code, 200)
        self.assertEqual(fetched, notification)

    def test_combined_filters_and_pagination(self):
        first = self.create()
        second = self.create(order_id="AMZ-OTHER")
        self.create("zalando")
        self.change(first, "RECEIVED")
        code, page, _ = self.api.call("GET", "/api/v1/returns?marketplace=amazon&status=RECEIVED&order_id=AMZ-2026-10001")
        self.assertEqual(code, 200)
        self.assertEqual(page["total"], 1)
        self.assertEqual(page["items"][0]["id"], first["id"])
        code, page, _ = self.api.call("GET", "/api/v1/returns?marketplace=amazon&limit=1&offset=1")
        self.assertEqual(code, 200)
        self.assertEqual(page["total"], 2)
        self.assertEqual([item["id"] for item in page["items"]], [first["id"]])
        self.assertNotEqual(first["id"], second["id"])

    def test_refund_and_idempotent_update(self):
        notification = self.create()
        for status in ("RECEIVED", "IN_REVIEW", "APPROVED", "REFUNDED"):
            updated = self.change(notification, status)
            self.assertEqual(updated["status"], status)
            self.assertGreater(updated["updated_at"], notification["updated_at"])
            notification = updated
        repeated = self.change(notification, "REFUNDED")
        self.assertEqual(repeated, notification)
        self.change(notification, "RECEIVED", expected=409)

    def test_rejection_is_terminal(self):
        notification = self.create("zalando")
        self.change(notification, "RECEIVED")
        self.change(notification, "REJECTED")
        self.change(notification, "APPROVED", expected=409)

    def test_automatic_approval_after_receipt(self):
        notification = self.create()
        self.change(notification, "RECEIVED")
        self.assertEqual(self.change(notification, "APPROVED")["status"], "APPROVED")

    def test_illegal_transition_does_not_mutate(self):
        notification = self.create()
        self.change(notification, "REFUNDED", expected=409)
        fetched = self.api.call("GET", "/api/v1/returns/" + notification["id"])[1]
        self.assertEqual(fetched, notification)

    def test_invalid_update_payloads(self):
        notification = self.create()
        for payload in ({}, {"status": "UNKNOWN"}, {"status": "RECEIVED", "id": "override"}):
            with self.subTest(payload=payload):
                code, _, _ = self.api.call("PATCH", f"/api/v1/returns/{notification['id']}/status", payload)
                self.assertEqual(code, 422)
        self.assertEqual(self.api.call("GET", "/api/v1/returns/" + notification["id"])[1], notification)

    def test_not_found_and_invalid_ids(self):
        unknown = str(uuid4())
        for method, path, payload, expected in (
            ("GET", "/api/v1/orders/UNKNOWN", None, 404),
            ("GET", "/api/v1/returns/" + unknown, None, 404),
            ("PATCH", f"/api/v1/returns/{unknown}/status", {"status": "RECEIVED"}, 404),
            ("GET", "/api/v1/returns/invalid", None, 422),
            ("PATCH", "/api/v1/returns/invalid/status", {"status": "RECEIVED"}, 422),
        ):
            with self.subTest(method=method, path=path):
                self.assertEqual(self.api.call(method, path, payload)[0], expected)

    def test_invalid_queries(self):
        for query in ("status=UNKNOWN", "marketplace=unknown", "limit=0", "offset=-1"):
            with self.subTest(query=query):
                self.assertEqual(self.api.call("GET", "/api/v1/returns?" + query)[0], 422)

    def test_invalid_notification_is_not_stored(self):
        payload = json.loads((COMPONENT_ROOT / "mock-data" / "invalid-return.json").read_text(encoding="utf-8"))
        self.assertEqual(self.api.call("POST", "/api/v1/returns", payload)[0], 422)
        self.assertEqual(self.api.call("GET", "/api/v1/returns")[1]["total"], 0)

    def test_status_survives_restart(self):
        notification = self.create()
        updated = self.change(notification, "RECEIVED")
        self.api.stop()
        self.api.start()
        self.assertEqual(self.api.call("GET", "/api/v1/returns/" + notification["id"])[1], updated)
        self.assertEqual(self.api.call("GET", "/api/v1/orders/AMZ-2026-10001")[0], 200)

    def test_concurrent_status_change_is_not_overwritten(self):
        notification = self.create()
        repository = ReturnRepository(self.database)
        return_id = UUID(notification["id"])
        first = repository.update_status(return_id, ReturnStatus.NEW, ReturnStatus.RECEIVED)
        self.assertIsNotNone(first)
        stale = repository.update_status(return_id, ReturnStatus.NEW, ReturnStatus.RECEIVED)
        self.assertIsNone(stale)
        self.assertEqual(repository.get(return_id), first)

    def test_demo_client(self):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "examples/demo.py", "--base-url", self.api.base_url],
            cwd=COMPONENT_ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Demonstration abgeschlossen", result.stdout)
        page = self.api.call("GET", "/api/v1/returns")[1]
        self.assertEqual({item["status"] for item in page["items"]}, {"REFUNDED", "REJECTED"})
        self.assertEqual(page["total"], 2)


class MigrationTests(unittest.TestCase):
    def test_existing_database_is_migrated_without_data_loss(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "legacy.sqlite3"
            return_id = str(uuid4())
            timestamp = "2026-10-29T14:15:00+00:00"
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("""CREATE TABLE return_notifications (
                    id TEXT PRIMARY KEY, marketplace TEXT NOT NULL, order_id TEXT NOT NULL,
                    customer_reference TEXT NOT NULL, item_sku TEXT NOT NULL,
                    item_name TEXT NOT NULL, return_reason TEXT NOT NULL,
                    registered_at TEXT NOT NULL, received_at TEXT NOT NULL
                )""")
                connection.execute(
                    "INSERT INTO return_notifications VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (return_id, "amazon", "LEGACY-ORDER", "CUSTOMER", "SKU", "Artikel", "Zu klein", timestamp, timestamp),
                )
            repository = ReturnRepository(database)
            repository.initialize()
            repository.initialize()
            notification = repository.get(UUID(return_id))
            if notification is None:
                self.fail("Migrierte Retourenmeldung wurde nicht gefunden")
            self.assertEqual(notification.order_id, "LEGACY-ORDER")
            self.assertEqual(notification.status, ReturnStatus.NEW)
            self.assertEqual(notification.updated_at, notification.received_at)
            self.assertIsNotNone(repository.update_status(UUID(return_id), ReturnStatus.NEW, ReturnStatus.RECEIVED))


if __name__ == "__main__":
    unittest.main()
