# Bot de WhatsApp — Recrutamento de Engenheiros Civis

Bot que responde os leads que clicam no anúncio "Clique para WhatsApp" do Facebook Ads.
Dá boas-vindas, explica a vaga em duas linhas, guia a instalação do app e o cadastro, tira
dúvidas de instalação sozinho, e só agenda ligação humana como último recurso.

- Entende texto **e áudio** (transcreve com Whisper)
- Responde em áudio (nota de voz) quando faz sentido, texto quando é link/lista/preço
- Consulta a base de conhecimento (`knowledge/produto.md`) via RAG da OpenAI
- Lembra do histórico de cada lead (SQLite) — não repete perguntas

## Stack

- **WhatsApp**: [APIBrasil](https://apibrasil.com.br) — plano WhatsApp Baileys
- **IA**: OpenAI (chat com file_search + Whisper + TTS)
- **Backend**: FastAPI

## 1. Contratar plano na APIBrasil

1. Entre em https://app.apibrasil.io/plano/montar
2. Escolha **WhatsApp Baileys** (R$ 12,90/conexão) → "Adicionar ao Plano"
3. Finalize a assinatura (mínimo R$ 69,90/mês)

## 2. Vincular seu número de WhatsApp

Depois que o plano ficar ativo:

1. Vá em **Credenciais** no painel — anote o **Bearer Token**
2. Vá em **Dispositivos** — crie um dispositivo novo pro WhatsApp Baileys
3. Anote o **Device Token** do dispositivo criado
4. Escaneie o QR code que aparece com o **WhatsApp do celular** — recomendo um chip
   novo/dedicado (não seu WhatsApp pessoal), pra separar o bot da sua conta

## 3. Instalar dependências

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configurar `.env`

Copie `.env.example` para `.env` e preencha:

```
APIBRASIL_BEARER_TOKEN=eyJ... (do passo 2)
APIBRASIL_DEVICE_TOKEN=... (do passo 2)
APIBRASIL_BASE_URL=          # deixe vazio pra usar o padrão
WEBHOOK_SECRET=escolha-um-valor-secreto
OPENAI_API_KEY=sk-... (de platform.openai.com/api-keys)
OPENAI_VECTOR_STORE_ID=      # em branco na primeira vez
```

## 5. Preencher a base de conhecimento

Edite `knowledge/produto.md` com os dados reais (nome da empresa, vaga, links do app,
passo a passo do cadastro, agendamento de ligação). Depois:

```powershell
python kb_setup.py
```

Ele imprime o `vector_store_id` na primeira execução — cole no `.env` como
`OPENAI_VECTOR_STORE_ID`. Reexecute sempre que editar `knowledge/produto.md`.

## 6. Rodar o bot + ngrok

Terminal 1:

```powershell
uvicorn app.main:app --reload
```

Terminal 2 (ngrok pra expor o webhook publicamente):

```powershell
ngrok http 8000
```

Anote a URL pública (algo tipo `https://abc123.ngrok-free.app`).

## 7. Configurar o webhook na APIBrasil

No painel da APIBrasil, na configuração do dispositivo criado, cadastre a URL do webhook:

```
https://SEU-NGROK.ngrok-free.app/webhook?token=SEU_WEBHOOK_SECRET
```

- Assine o evento `MESSAGES_UPSERT` (o único que o bot escuta)
- O `?token=...` bate com `WEBHOOK_SECRET` do `.env` — é o filtro pra rejeitar
  requisições que não sejam da APIBrasil

## 8. Testar

Mande uma mensagem de texto do seu WhatsApp pessoal pro número do bot:
- Deve responder com boas-vindas + explicação curta da vaga (em áudio)
- Manda um áudio: o bot transcreve, entende e responde
- Numa segunda mensagem, ele não deve repetir pergunta já respondida (checa
  `conversations.db` na raiz)

## Se algo vier diferente

Se a APIBrasil mandar o webhook num formato ligeiramente diferente do esperado, o
único ponto que ajusta é a função `_parse_message` em `app/main.py`. Manda pra mim o
JSON que o webhook chegou (dá pra ver no log do uvicorn) que eu ajusto.

## 9. Produção (depois)

Sugestão: [Railway](https://railway.app) ou [Render](https://render.com). Passos:

1. Suba o projeto num repo Git.
2. Crie um serviço apontando pro repo.
3. Adicione as mesmas variáveis do `.env` no painel da plataforma.
4. Comando de start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Atualize a URL do webhook na APIBrasil pra apontar pra URL pública do serviço.
