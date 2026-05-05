import base64
import json
from pathlib import Path

import pytest

from src import app


def test_load_quiz_bank(tmp_path: Path) -> None:
    sample = {"questions": [{"question": "Test?", "options": ["A", "B"]}]}
    target = tmp_path / "quiz.json"
    target.write_text(json.dumps(sample), encoding="utf-8")

    bank = app.load_quiz_bank(target)

    assert bank == sample


def test_pick_random_question_is_deterministic() -> None:
    questions = [
        {"question": "First?", "options": ["A", "B"]},
        {"question": "Second?", "options": ["C", "D"]},
    ]
    rng = __import__("random").Random(1)

    picked = app.pick_random_question(questions, rng=rng)

    assert picked["question"] == "First?"


def test_normalize_poll_options() -> None:
    options = ["Yes", "", "  No  ", 123, None]

    cleaned = app.normalize_poll_options(options)

    assert cleaned == ["Yes", "No"]


def test_parse_event_body_base64() -> None:
    payload = {"chat_id": 123}
    raw = json.dumps(payload).encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")

    body = app.parse_event_body({"body": encoded, "isBase64Encoded": True})

    assert body == payload


def test_handle_lambda_request_without_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sample = {"questions": [{"question": "Test?", "options": ["A", "B"]}]}
    target = tmp_path / "quiz.json"
    target.write_text(json.dumps(sample), encoding="utf-8")

    monkeypatch.setenv("QUIZ_BANK_PATH", str(target))
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    response = app.handle_lambda_request({"body": "{}"}, None)
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["sent"] is False
    assert body["message"] == "Test?"
    assert body["poll"]["question"] == "Test?"
    assert body["poll"]["options"] == ["A", "B"]
