import sqlite3
from pathlib import Path

from broker import Broker
from events import ANY_STATUS, ReturnStatusChanged

DATABASE = Path(__file__).parent / "data" / "prozesslog.sqlite3"


def open_event_log(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE IF NOT EXISTS events "
        "(event_id TEXT PRIMARY KEY, return_id TEXT, status TEXT, occurred_at TEXT, source TEXT)"
    )
    return db


def record(db: sqlite3.Connection, event: ReturnStatusChanged) -> None:
    with db:
        newly_recorded = db.execute(
            "INSERT OR IGNORE INTO events VALUES (?, ?, ?, ?, ?)",
            (event.event_id, event.return_id, event.status, event.occurred_at, event.source),
        ).rowcount
    if newly_recorded:
        print(f"{event.occurred_at}  {event.return_id}  {event.status}")


if __name__ == "__main__":
    DATABASE.parent.mkdir(exist_ok=True)
    db = open_event_log(DATABASE)
    Broker().subscribe("prozesslog", [ANY_STATUS], lambda event: record(db, event))
