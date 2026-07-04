"""Integração com Groq (Llama 3.3 70B).

- Free tier: ~30 requisições/min, sem cadastro de cartão.
- API compatível OpenAI: mensagens no formato role/content.
- Sempre responde em texto (usuário escolheu "sem áudio").
"""

from groq import Groq

from app.config import CHAT_MODEL, GROQ_API_KEY, KNOWLEDGE_PATH

client = Groq(api_key=GROQ_API_KEY)

_KNOWLEDGE_TEXT = KNOWLEDGE_PATH.read_text(encoding="utf-8")

SYSTEM_PROMPT = f"""Você é um recrutador virtual da empresa por WhatsApp, atendendo candidatos que clicaram num anúncio de vaga de Engenheiro Civil no Facebook.

Objetivo do atendimento (nessa ordem):
1. Dar boas-vindas e agradecer o interesse na vaga.
2. Explicar de forma bem curta o que a empresa faz e do que se trata a vaga (1-2 frases, sem despejar tudo).
3. Mandar o link do app e instruir a instalar: abrir o link, clicar em "Instalar" na página, e seguir o fluxo normal da loja.
4. Se o candidato tiver qualquer dúvida ou dificuldade, TENTE resolver você mesmo primeiro, com paciência e passo a passo. Só escale para agendamento de ligação humana como último recurso — quando você já tentou explicar de mais de uma forma e o candidato continua travado, ou quando ele explicitamente pede pra falar com alguém.

Regras:
- Use a base de conhecimento abaixo para responder com precisão. Não invente informação que não esteja lá — se faltar dado, diga que vai verificar e agende a ligação.
- Olhe o histórico da conversa antes de responder: nunca repita uma pergunta ou informação que já foi dada.
- Uma coisa de cada vez — não jogue toda a informação numa mensagem só. Guie o candidato passo a passo.
- Ao ajudar com problemas de instalação: pergunte primeiro qual é o sintoma específico (deu erro? qual erro? não abre? não baixa?) antes de sair chutando soluções.
- Seja natural, cordial e objetivo, como um recrutador humano experiente. Nada de linguagem robótica ou saudações desnecessárias em toda mensagem.
- Se receber um áudio, responda pedindo educadamente que a pessoa digite a dúvida (o bot só entende texto no momento).
- Responda sempre em português brasileiro.

# Base de conhecimento

{_KNOWLEDGE_TEXT}
"""


def generate_reply(history: list[dict], user_message: str) -> str:
    """Gera resposta em texto a partir do histórico + mensagem atual.

    Histórico interno usa {"role": "user"|"assistant", "content": str},
    que já é o mesmo formato aceito pela API do Groq (OpenAI-compatible).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    return (response.choices[0].message.content or "").strip()
