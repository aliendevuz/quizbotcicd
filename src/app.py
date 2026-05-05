import base64
import json
import os
import random
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_QUIZ_PATH = Path(__file__).resolve().parent.parent / "quiz_bank.json"


def load_quiz_bank(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def get_questions(bank: Dict[str, Any]) -> List[Dict[str, Any]]:
    questions = bank.get("questions")
    if not isinstance(questions, list):
        return []
    return [q for q in questions if isinstance(q, dict)]


def pick_random_question(questions: List[Dict[str, Any]], rng: Optional[random.Random] = None) -> Dict[str, Any]:
    if not questions:
        return {}
    chooser = rng or random
    return chooser.choice(questions)


def normalize_poll_options(options: Any) -> List[str]:
    if not isinstance(options, list):
        return []
    cleaned: List[str] = []
    for option in options:
        if isinstance(option, str):
            value = option.strip()
            if value:
                cleaned.append(value)
    return cleaned


def _decode_body(event: Dict[str, Any]) -> Optional[str]:
    body = event.get("body")
    if body is None:
        return None
    if not isinstance(body, str):
        return None
    if event.get("isBase64Encoded"):
        try:
            decoded = base64.b64decode(body)
            return decoded.decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
    return body


def parse_event_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = _decode_body(event)
    if body:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    if isinstance(event, dict):
        return event
    return {}


def extract_chat_id(payload: Dict[str, Any]) -> Optional[int]:
    if "chat_id" in payload and isinstance(payload["chat_id"], int):
        return payload["chat_id"]

    message = payload.get("message") or payload.get("edited_message")
    if isinstance(message, dict):
        chat = message.get("chat")
        if isinstance(chat, dict) and isinstance(chat.get("id"), int):
            return chat["id"]

    callback = payload.get("callback_query")
    if isinstance(callback, dict):
        message = callback.get("message")
        if isinstance(message, dict):
            chat = message.get("chat")
            if isinstance(chat, dict) and isinstance(chat.get("id"), int):
                return chat["id"]

    return None


def send_telegram_poll(
    token: str,
    chat_id: int,
    question_text: str,
    options: List[str],
    correct_option_id: Optional[int] = None,
) -> Dict[str, Any]:
    api_root = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")
    url = f"{api_root}/bot{token}/sendPoll"
    body: Dict[str, Any] = {
        "chat_id": chat_id,
        "question": question_text,
        "options": options,
        "type": "quiz",
        "is_anonymous": False,
        "allows_multiple_answers": False,
    }
    if correct_option_id is not None:
        body["correct_option_id"] = correct_option_id
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        content = response.read().decode("utf-8")
        return json.loads(content)


def handle_lambda_request(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    quiz_path = Path(os.environ.get("QUIZ_BANK_PATH", str(DEFAULT_QUIZ_PATH)))
    bank = load_quiz_bank(quiz_path)
    question = pick_random_question(get_questions(bank))
    question_text = str(question.get("question", "")).strip()
    poll_options = normalize_poll_options(question.get("options"))
    correct_option_id = question.get("correct_option") if isinstance(question.get("correct_option"), int) else None
    if correct_option_id is not None and not (0 <= correct_option_id < len(poll_options)):
        correct_option_id = None

    payload = parse_event_body(event)
    chat_id = extract_chat_id(payload)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    sent = False
    telegram_response = None
    if token and chat_id and question_text and poll_options:
        telegram_response = send_telegram_poll(
            token,
            chat_id,
            question_text,
            poll_options,
            correct_option_id=correct_option_id,
        )
        sent = bool(telegram_response.get("ok")) if isinstance(telegram_response, dict) else True

    body = {
        "ok": True,
        "sent": sent,
        "message": question_text,
        "question": question,
        "poll": {
            "question": question_text,
            "options": poll_options,
            "correct_option_id": correct_option_id,
        },
    }
    if telegram_response is not None:
        body["telegram"] = telegram_response

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
