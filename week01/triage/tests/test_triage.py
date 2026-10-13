"""Tests for triage(). They use FakeClient, so no network and no API key are needed.

They fail until you finish the TODOs in triage.py. That is the point:
make them pass one at a time, and read each failure message before you change anything.
"""

import json
import sys
from pathlib import Path

import pytest

# The code lives one folder up. This line lets `pytest` find it from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm import FakeClient  # noqa: E402
from models import Category, Priority, Triage, TriageError  # noqa: E402
from triage import triage  # noqa: E402

TICKET = "Subject: Charged twice\n\nMy UPI payment was debited two times. Please refund one."

VALID = json.dumps(
    {
        "category": "billing",
        "priority": "P2",
        "summary": "Customer was charged twice by UPI and wants one payment refunded.",
        "needs_human": True,
        "reason": "Money moved wrongly, so it is billing and needs a person quickly.",
    }
)

# "urgent" is not one of our priorities or categories, so Pydantic must reject this.
INVALID = json.dumps(
    {
        "category": "urgent",
        "priority": "P2",
        "summary": "Charged twice.",
        "needs_human": True,
        "reason": "Money problem.",
    }
)


def read_trace_lines(trace_dir: Path) -> list[dict]:
    files = list(trace_dir.glob("*.jsonl"))
    assert len(files) == 1, "expected exactly one trace file for today"
    return [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]


def test_valid_response_returns_triage(tmp_path):
    client = FakeClient([VALID])

    result = triage(TICKET, client, trace_dir=tmp_path)

    assert isinstance(result, Triage)
    assert result.category is Category.BILLING
    assert result.priority is Priority.P2
    assert result.needs_human is True
    assert len(client.calls) == 1


def test_invalid_then_valid_retries_once_and_tells_the_model_why(tmp_path):
    client = FakeClient([INVALID, VALID])

    result = triage(TICKET, client, trace_dir=tmp_path)

    assert result.category is Category.BILLING
    assert len(client.calls) == 2
    # The retry must be informed: the validation error names the bad field.
    assert "category" in client.calls[1].user
    assert client.calls[1].user != client.calls[0].user


def test_invalid_twice_raises_triage_error_without_a_third_call(tmp_path):
    client = FakeClient([INVALID, INVALID])

    with pytest.raises(TriageError):
        triage(TICKET, client, trace_dir=tmp_path)

    assert len(client.calls) == 2


def test_every_attempt_writes_a_trace_line(tmp_path):
    client = FakeClient([INVALID, VALID])

    triage(TICKET, client, trace_dir=tmp_path)

    first, second = read_trace_lines(tmp_path)
    expected_keys = {"timestamp", "model", "attempt", "latency_ms", "ok", "error", "input_chars"}
    assert expected_keys <= first.keys()
    assert (first["attempt"], first["ok"]) == (1, False)
    assert first["error"]  # a failed attempt says why
    assert (second["attempt"], second["ok"]) == (2, True)
    assert second["error"] is None
    assert second["model"] == "fake-model"
    assert second["input_chars"] == len(TICKET)
