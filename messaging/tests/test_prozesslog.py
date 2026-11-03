from events import ReturnStatus, ReturnStatusChanged
from prozesslog import open_event_log, record


def test_doppelt_zugestelltes_ereignis_wird_nur_einmal_protokolliert(tmp_path):
    path = tmp_path / "prozesslog.sqlite3"
    event = ReturnStatusChanged("RET-1", ReturnStatus.RECEIVED, source="test")

    before_restart = open_event_log(path)
    record(before_restart, event)
    after_restart = open_event_log(path)
    record(after_restart, event)

    rows = after_restart.execute("SELECT event_id, status FROM events").fetchall()
    assert rows == [(event.event_id, "RECEIVED")]
