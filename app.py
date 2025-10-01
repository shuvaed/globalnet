from fastapi import FastAPI, Request
import os, requests

app = FastAPI()

AGENT_URL_CLIENT  = os.getenv("AGENT_PUBLIC_URL")          # публичный URL агентной системы (client)
AGENT_URL_MANAGER = os.getenv("AGENT_PUBLIC_URL_MANAGER")  # опционально, для /manager
AGENT_KEY         = os.getenv("AGENT_API_KEY", "")
TG_TOKEN          = os.getenv("TELEGRAM_TOKEN", "")

def ask_agent(url, text, chat_id):
    headers = {"Content-Type": "application/json"}
    if AGENT_KEY:
        headers["Authorization"] = f"Bearer {AGENT_KEY}"
    r = requests.post(url, json={"session_id": str(chat_id), "message": text},
                      headers=headers, timeout=25)
    r.raise_for_status()
    data = r.json()
    return data.get("answer") or data.get("text") or "Нет ответа от агента."

def send_tg(chat_id, text):
    if not TG_TOKEN:
        return  # чтобы сервис работал даже без токена
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/tg")
async def tg(req: Request):
    upd = await req.json()
    msg = (upd.get("message") or upd.get("edited_message")) or {}
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    text = (msg.get("text") or "").strip()

    if not chat_id or not text:
        return {"ok": True}

    # роутинг: /manager ... → во внутреннего агента (если задан)
    is_manager = text.startswith("/manager")
    if is_manager:
        text = text[len("/manager"):].strip()

    agent_url = (AGENT_URL_MANAGER if is_manager and AGENT_URL_MANAGER else AGENT_URL_CLIENT)

    try:
        if agent_url:
            answer = ask_agent(agent_url, text, chat_id)
        else:
            answer = f"Эхо: {text} (AGENT_PUBLIC_URL не задан)"
    except Exception as e:
        answer = f"Пока не могу ответить: {e}"

    send_tg(chat_id, answer)
    return {"ok": True}
