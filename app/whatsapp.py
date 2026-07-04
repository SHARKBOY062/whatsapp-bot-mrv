"""Cliente da APIBrasil — WhatsApp Baileys.

- Base URL: https://gateway.apibrasil.io/api/v2
- Headers: Authorization Bearer + DeviceToken + Content-Type application/json
- POST /evolution/message/sendText → envia texto

Baileys/APIBrasil tem uma pegadinha com números brasileiros de celular:
alguns aceitam o '9' extra (13 dígitos), outros só sem o '9' (12 dígitos).
Depende da região/lead. O `send_text` tenta os 2 formatos automaticamente.
"""

import logging

import httpx

from app.config import (
    APIBRASIL_BASE_URL,
    APIBRASIL_BEARER_TOKEN,
    APIBRASIL_DEVICE_TOKEN,
)

logger = logging.getLogger("whatsapp-bot")

HEADERS = {
    "Authorization": f"Bearer {APIBRASIL_BEARER_TOKEN}",
    "DeviceToken": APIBRASIL_DEVICE_TOKEN,
    "Content-Type": "application/json",
}


def send_text(to: str, body: str) -> None:
    """Envia texto tentando variações do número BR se der 400."""
    digits = _digits_only(to)
    variants = _phone_variants(digits)

    last_error: Exception | None = None
    for phone in variants:
        payload = {
            "number": phone,
            "text": body,
            "options": {"delay": 1200, "presence": "composing"},
            "homolog": False,
        }
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{APIBRASIL_BASE_URL}/evolution/message/sendText",
                    headers=HEADERS,
                    json=payload,
                )
                if resp.status_code < 300:
                    logger.info("Enviado com sucesso pra %s (variante %s)", to, phone)
                    return
                # Log detalhado do body de erro
                logger.warning(
                    "Falha sendText pra %s (variante %s): %d %s",
                    to, phone, resp.status_code, resp.text[:200],
                )
                last_error = httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=resp.request, response=resp
                )
        except Exception as exc:
            last_error = exc
            logger.exception("Erro de conexão sendText pra %s (variante %s)", to, phone)

    # Todas as variantes falharam
    if last_error:
        raise last_error


def _digits_only(number: str) -> str:
    number = number.split("@")[0]
    return "".join(ch for ch in number if ch.isdigit())


def _phone_variants(digits: str) -> list[str]:
    """Retorna variantes de tentativa pra número BR (com/sem o 9 extra).
    - Se tem 13 dígitos (55 + DDD + 9 + 8 dígitos): tenta sem 9 primeiro,
      depois com 9.
    - Se tem 12 dígitos (55 + DDD + 8 dígitos): tenta com 9, depois sem.
    - Outros formatos: tenta como está.
    """
    if len(digits) == 13 and digits.startswith("55") and digits[4] == "9":
        without_9 = digits[:4] + digits[5:]
        return [without_9, digits]
    if len(digits) == 12 and digits.startswith("55"):
        with_9 = digits[:4] + "9" + digits[4:]
        return [digits, with_9]
    return [digits]
