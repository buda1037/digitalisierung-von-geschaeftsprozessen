import json

import pytest

from events import InvalidMessage, ReturnStatus, ReturnStatusChanged


def message(**changes) -> bytes:
    valid = json.loads(ReturnStatusChanged("RET-1", ReturnStatus.NEW, source="test").to_json())
    return json.dumps(valid | changes).encode()


def test_json_roundtrip_erhaelt_alle_felder():
    event = ReturnStatusChanged("RET-1", ReturnStatus.IN_REVIEW, source="test")

    assert ReturnStatusChanged.from_json(event.to_json()) == event


def test_routing_key_enthaelt_den_status():
    assert ReturnStatus.IN_REVIEW.routing_key == "retoure.status.in_review"


def test_unbekannte_felder_werden_ignoriert():
    assert ReturnStatusChanged.from_json(message(neues_feld=42)).return_id == "RET-1"


@pytest.mark.parametrize(
    "body",
    [
        b"kein JSON",
        b"[]",
        b'{"status": "NEW"}',
        message(status="UNBEKANNT"),
        message(occurred_at="gestern"),
        message(occurred_at="2026-11-03T10:00:00"),
    ],
    ids=[
        "kein-json",
        "kein-objekt",
        "fehlende-felder",
        "unbekannter-status",
        "unlesbarer-zeitpunkt",
        "zeitpunkt-ohne-zeitzone",
    ],
)
def test_ungueltige_nachricht_wird_abgewiesen(body):
    with pytest.raises(InvalidMessage):
        ReturnStatusChanged.from_json(body)
