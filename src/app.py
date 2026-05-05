import base64
import json
import os
import random
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def format_question_text(question: Dict[str, Any]) -> str:
    prompt = question.get("question", "")
    options = question.get("options", [])
    lines = [f"Savol: {prompt}"]
    if isinstance(options, list):
        for index, option in enumerate(options, start=1):
            lines.append(f"{index}) {option}")
    return "\n".join(lines)


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


def send_telegram_message(token: str, chat_id: int, text: str) -> Dict[str, Any]:
    api_root = os.environ.get("TELEGRAM_API_URL", "https://api.telegram.org")
    url = f"{api_root}/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
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
    text = format_question_text(question)

    payload = parse_event_body(event)
    chat_id = extract_chat_id(payload)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    sent = False
    telegram_response = None
    if token and chat_id and text:
        telegram_response = send_telegram_message(token, chat_id, text)
        sent = bool(telegram_response.get("ok")) if isinstance(telegram_response, dict) else True

    body = {
        "ok": True,
        "sent": sent,
        "message": text,
        "question": question,
    }
    if telegram_response is not None:
        body["telegram"] = telegram_response

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
