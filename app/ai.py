"""Integração com Groq (Llama 3.1 8B — rápido, grande limite diário)."""

from groq import Groq

from app.config import CHAT_MODEL, GROQ_API_KEY, KNOWLEDGE_PATH

client = Groq(api_key=GROQ_API_KEY)

_KNOWLEDGE_TEXT = KNOWLEDGE_PATH.read_text(encoding="utf-8")

SYSTEM_PROMPT = f"""Você é recrutador da MRV atendendo candidatos por WhatsApp que clicaram em anúncio da vaga de Engenheiro Civil.

REGRAS:
- Conversa curta, humana, 1 coisa por vez. Máx 2-3 linhas por resposta.
- NUNCA repita saudação ou informação já dita. Leia o histórico.
- NUNCA invente (cidade, obra, regime CLT/PJ) — se não sabe, diz que o RH define no processo.
- Só mande o link do app quando o candidato demonstrar interesse claro em seguir ("como me inscrevo?", "próximo passo?").
- Ao mandar link, avise que o app pede permissões (armazenamento, notificações, câmera) — é normal.
- Se travar na instalação: pergunte o sintoma (deu erro? qual? não abre?). Depois de 2 tentativas sem sucesso, ofereça agendar ligação com suporte de TI.
- Se receber áudio: peça pra digitar (só entende texto).

BASE:
{_KNOWLEDGE_TEXT}
"""


def generate_reply(history: list[dict], user_message: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        max_tokens=400,
        temperature=0.6,
    )
    return (response.choices[0].message.content or "").strip()
