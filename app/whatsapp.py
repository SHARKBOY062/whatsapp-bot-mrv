"""Cliente da APIBrasil — WhatsApp Baileys.

- Base URL: https://gateway.apibrasil.io/api/v2
- Headers: Authorization Bearer + DeviceToken + Content-Type application/json
- POST /evolution/message/sendText → envia texto

Só usamos envio de texto (áudio ficou de fora nesta versão do bot).
"""

import httpx

from app.config import (
    APIBRASIL_BASE_URL,
    APIBRASIL_BEARER_TOKEN,
    APIBRASIL_DEVICE_TOKEN,
)

HEADERS = {
    "Authorization": f"Bearer {APIBRASIL_BEARER_TOKEN}",
    "DeviceToken": APIBRASIL_DEVICE_TOKEN,
    "Content-Type": "application/json",
}


def send_text(to: str, body: str) -> None:
    payload = {
        "number": _normalize_phone(to),
        "text": body,
        "options": {"delay": 1200, "presence": "composing"},
        "homolog": False,
    }
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{APIBRASIL_BASE_URL}/evolution/message/sendText",
            headers=HEADERS,
            json=payload,
        )
        resp.raise_for_status()


def _normalize_phone(number: str) -> str:
    number = number.split("@")[0]
    return "".join(ch for ch in number if ch.isdigit())
