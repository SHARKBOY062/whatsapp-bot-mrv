import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# APIBrasil — WhatsApp Baileys
APIBRASIL_BEARER_TOKEN = os.environ["APIBRASIL_BEARER_TOKEN"]
APIBRASIL_DEVICE_TOKEN = os.environ["APIBRASIL_DEVICE_TOKEN"]
APIBRASIL_BASE_URL = os.environ.get(
    "APIBRASIL_BASE_URL", "https://gateway.apibrasil.io/api/v2"
)

# Segredo simples pra validar que o webhook recebido é mesmo da APIBrasil
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

# Groq — Llama 3.3 (grátis, ~30 req/min)
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
CHAT_MODEL = "llama-3.3-70b-versatile"

# Base de conhecimento
KNOWLEDGE_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "produto.md"

MAX_HISTORY_MESSAGES = 30
