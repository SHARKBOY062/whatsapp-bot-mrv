"""Webhook FastAPI: recebe mensagens da APIBrasil, responde via Groq (Llama).

Comportamentos especiais:
- Primeira interação: pequeno atraso (8s) pra dar tempo da mensagem de saudação
  do WhatsApp Business chegar antes do bot entrar em cena.
- Follow-up: endpoint `/check-stale` (chamado por GitHub Actions) envia
  mensagem de re-engajamento pra leads silenciosos há 30+ minutos.
"""

import asyncio
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

FOLLOW_UP_MESSAGE = (
    "Oi! Vi que ficou por aqui — você conseguiu instalar o app da MRV? "
    "Se estiver com alguma dificuldade ou dúvida, é só me responder que "
    "eu te ajudo. Se preferir, posso agendar uma ligação rapidinha com "
    "nosso time pra destravar 😊"
)

# Pequena pausa antes de responder — deixa a resposta parecer menos "bot"
# (envio instantâneo entrega que é máquina). Também dá tempo pro lead
# terminar de digitar se estiver mandando várias mensagens em sequência.
GREETING_DELAY_SECONDS = 2

# Silêncio (minutos) do lead antes de disparar o follow-up
STALE_MINUTES = 30


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

    # APIBrasil não coloca campo `event`; detectamos mensagem via data.key + data.message
    data = body.get("data")
    if not (isinstance(data, dict) and data.get("key") and data.get("message")):
        return {"status": "ignored"}

    parsed = _parse_message(data)
    if parsed is None:
        return {"status": "ignored"}

    phone, kind, user_text = parsed

    if kind == "audio":
        memory.save_message(phone, "user", "[áudio recebido]")
        memory.save_message(phone, "assistant", AUDIO_FALLBACK_REPLY)
        whatsapp.send_text(phone, AUDIO_FALLBACK_REPLY)
        return {"status": "ok"}

    logger.info("Mensagem de %s: %s", phone, user_text)

    memory.save_message(phone, "user", user_text)

    # Pequena pausa antes de responder pra não parecer bot instantâneo
    await asyncio.sleep(GREETING_DELAY_SECONDS)

    history = memory.get_history(phone, MAX_HISTORY_MESSAGES)
    reply = ai.generate_reply(history[:-1], user_text) or (
        "Deu um probleminha aqui. Pode tentar de novo daqui a pouquinho?"
    )

    memory.save_message(phone, "assistant", reply)
    whatsapp.send_text(phone, reply)
    return {"status": "ok"}


@app.post("/check-stale")
async def check_stale(request: Request):
    """Roda periodicamente (via GitHub Actions). Envia follow-up para leads
    silenciosos há mais de STALE_MINUTES minutos — uma vez só por conversa."""
    if WEBHOOK_SECRET:
        provided = (
            request.headers.get("X-Webhook-Secret")
            or request.query_params.get("token")
        )
        if provided != WEBHOOK_SECRET:
            return Response(status_code=403)

    stale = memory.get_stale_phones(STALE_MINUTES)
    if not stale:
        return {"followed_up": 0}

    for phone in stale:
        try:
            whatsapp.send_text(phone, FOLLOW_UP_MESSAGE)
            memory.save_message(phone, "assistant", FOLLOW_UP_MESSAGE, is_follow_up=True)
            logger.info("Follow-up enviado para %s", phone)
        except Exception as exc:
            logger.exception("Falha no follow-up para %s: %s", phone, exc)

    return {"followed_up": len(stale)}


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
