"""Webhook FastAPI: recebe mensagens da APIBrasil, responde via Claude."""

import logging

from fastapi import FastAPI, Request, Response

from app import ai, memory, whatsapp
from app.config import MAX_HISTORY_MESSAGES, WEBHOOK_SECRET

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp-bot")

app = FastAPI()

AUDIO_FALLBACK_REPLY = (
    "Desculpa, ainda não consigo entender áudio 🙏 "
    "Pode digitar a sua pergunta que eu te respondo aqui na hora?"
)


@app.get("/")
def healthcheck():
    return {"status": "ok"}


@app.post("/webhook")
async def receive_webhook(request: Request):
    if WEBHOOK_SECRET:
        provided = (
            request.headers.get("X-Webhook-Secret")
            or request.query_params.get("token")
        )
        if provided != WEBHOOK_SECRET:
            logger.warning("Webhook rejeitado — segredo inválido")
            return Response(status_code=403)

    body = await request.json()
    logger.info("Webhook recebido: event=%s | body=%s", body.get("event"), body)

    event = body.get("event") or ""
    if "messages.upsert" not in event and "message" not in event.lower():
        return {"status": "ignored"}

    parsed = _parse_message(body.get("data") or {})
    if parsed is None:
        return {"status": "ignored"}

    phone, kind, user_text = parsed

    if kind == "audio":
        # Salva evento no histórico e responde pedindo texto
        memory.save_message(phone, "user", "[áudio recebido]")
        memory.save_message(phone, "assistant", AUDIO_FALLBACK_REPLY)
        whatsapp.send_text(phone, AUDIO_FALLBACK_REPLY)
        return {"status": "ok"}

    logger.info("Mensagem de %s: %s", phone, user_text)

    memory.save_message(phone, "user", user_text)
    history = memory.get_history(phone, MAX_HISTORY_MESSAGES)

    reply = ai.generate_reply(history, user_text)
    if not reply:
        reply = "Deu um probleminha aqui. Pode tentar de novo daqui a pouquinho?"

    memory.save_message(phone, "assistant", reply)
    whatsapp.send_text(phone, reply)
    return {"status": "ok"}


def _parse_message(data: dict) -> tuple[str, str, str] | None:
    """Retorna (telefone, tipo, texto). `tipo` = "text" ou "audio"."""
    key = data.get("key") or {}
    if key.get("fromMe"):
        return None

    jid = key.get("remoteJid") or data.get("phone") or ""
    if not jid or "@g.us" in jid:  # ignora grupos
        return None
    phone = jid.split("@")[0]

    message = data.get("message") or {}
    msg_type = data.get("messageType") or ""

    if "conversation" in message:
        return (phone, "text", message["conversation"])

    if "extendedTextMessage" in message:
        return (phone, "text", message["extendedTextMessage"].get("text", ""))

    if "audioMessage" in message or msg_type == "audioMessage":
        return (phone, "audio", "")

    logger.info("Tipo de mensagem não suportado: %s", msg_type)
    return None
