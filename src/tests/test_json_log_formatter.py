import json
import logging
import sys
from datetime import datetime, timezone

from kedro_graphql.logs.json_log_formatter import JSONFormatter


def test_json_formatter_preserves_record_metadata_and_nested_extra():
    record = logging.LogRecord(
        "toy.pipeline", logging.WARNING, __file__, 1, "node %s", ("run",), None
    )
    record.created = 1_735_734_645.25
    record.context = {
        "node": "toy",
        "values": [1, {"ok": True}],
        "started_at": datetime(2025, 1, 1, 12, 30, tzinfo=timezone.utc),
        "error": ValueError("nested failure"),
    }

    payload = json.loads(JSONFormatter().format(record))

    assert payload["message"] == "node run"
    assert payload["time"] == "2025-01-01T12:30:45.250000+00:00"
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "toy.pipeline"
    assert payload["context"] == {
        "node": "toy",
        "values": [1, {"ok": True}],
        "started_at": "2025-01-01T12:30:00+00:00",
        "error": {"type": "ValueError", "message": "nested failure"},
    }


def test_json_formatter_preserves_exception_details():
    try:
        raise ValueError("toy failure")
    except ValueError:
        record = logging.LogRecord(
            "toy.pipeline",
            logging.ERROR,
            __file__,
            1,
            "node failed",
            (),
            sys.exc_info(),
        )

    payload = json.loads(JSONFormatter().format(record))

    assert "Traceback (most recent call last)" in payload["exc_info"]
    assert "ValueError: toy failure" in payload["exc_info"]
