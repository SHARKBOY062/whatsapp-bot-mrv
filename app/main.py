"""Webhook FastAPI: recebe mensagens da APIBrasil, responde via Groq (Llama)."""

import asyncio
import logging
import traceback

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

GREETING_DELAY_SECONDS = 2
STALE_MINUTES = 30


@app.get("/")
def healthcheck():
    return {"status": "ok"}


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Sempre retorna 200 — se algo falhar internamente, log detalhado mas
    não deixa a APIBrasil reentregar em loop."""
    try:
        if WEBHOOK_SECRET:
            provided = (
                request.headers.get("X-Webhook-Secret")
                or request.query_params.get("token")
            )
            if provided != WEBHOOK_SECRET:
                logger.warning("Webhook rejeitado — segredo inválido")
                return Response(status_code=403)

        body = await request.json()
        data = body.get("data")
        if not (isinstance(data, dict) and data.get("key") and data.get("message")):
            return {"status": "ignored"}

        parsed = _parse_message(data)
        if parsed is None:
            return {"status": "ignored"}

        phone, kind, user_text = parsed

        # Áudio: resposta padrão e retorna
        if kind == "audio":
            try:
                memory.save_message(phone, "user", "[áudio recebido]")
                memory.save_message(phone, "assistant", AUDIO_FALLBACK_REPLY)
                whatsapp.send_text(phone, AUDIO_FALLBACK_REPLY)
            except Exception:
                logger.exception("Erro processando áudio de %s", phone)
            return {"status": "ok"}

        logger.info("Mensagem de %s: %s", phone, user_text)

        # Salva msg do lead (etapa 1) — se falhar aqui, ignora
        try:
            memory.save_message(phone, "user", user_text)
        except Exception:
            logger.exception("Falha ao salvar mensagem do lead %s", phone)

        # Pausa curta
        await asyncio.sleep(GREETING_DELAY_SECONDS)

        # Gera resposta (etapa 2) — se Groq falhar, log mas não crasha
        try:
            history = memory.get_history(phone, MAX_HISTORY_MESSAGES)
            # get_history já inclui a msg atual (que acabou de ser salva);
            # passa histórico até antes dela pro modelo:
            reply = ai.generate_reply(history[:-1], user_text)
        except Exception:
            logger.exception("Falha ao gerar resposta pra %s", phone)
            reply = "Deu um probleminha aqui. Pode me repetir daqui a pouquinho?"

        if not reply:
            reply = "Deu um probleminha aqui. Pode me repetir daqui a pouquinho?"

        # Salva resposta (etapa 3)
        try:
            memory.save_message(phone, "assistant", reply)
        except Exception:
            logger.exception("Falha ao salvar resposta do bot pra %s", phone)

        # Envia via WhatsApp (etapa 4) — se APIBrasil falhar, log
        try:
            whatsapp.send_text(phone, reply)
        except Exception:
            logger.exception("Falha ao enviar mensagem pra %s (msg='%s')", phone, reply[:80])

        return {"status": "ok"}

    except Exception:
        # Blindagem final — nenhum erro leve devolve 500 pra APIBrasil
        logger.error("ERRO NÃO TRATADO NO WEBHOOK:\n%s", traceback.format_exc())
        return {"status": "error_logged"}


@app.post("/check-stale")
async def check_stale(request: Request):
    if WEBHOOK_SECRET:
        provided = (
            request.headers.get("X-Webhook-Secret")
            or request.query_params.get("token")
        )
        if provided != WEBHOOK_SECRET:
            return Response(status_code=403)

    try:
        stale = memory.get_stale_phones(STALE_MINUTES)
    except Exception:
        logger.exception("Falha ao consultar stale phones")
        return {"followed_up": 0, "error": True}

    if not stale:
        return {"followed_up": 0}

    sent = 0
    for phone in stale:
        try:
            whatsapp.send_text(phone, FOLLOW_UP_MESSAGE)
            memory.save_message(phone, "assistant", FOLLOW_UP_MESSAGE, is_follow_up=True)
            logger.info("Follow-up enviado para %s", phone)
            sent += 1
        except Exception:
            logger.exception("Falha no follow-up para %s", phone)

    return {"followed_up": sent}


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
