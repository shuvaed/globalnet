from fastapi import FastAPI, Request
import os, requests, time

app = FastAPI()

TG_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
AGENT_URL  = os.getenv("AGENT_PUBLIC_URL", "")
AGENT_KEY  = os.getenv("AGENT_API_KEY", "")

BTN_CLIENT = "🤖 Ассистент GlobalNet"
SESSIONS = {}  # chat_id -> {"active": True/False, "ts": time.time()}

def send_tg(chat_id, text, reply_markup=None):
    if not TG_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(url, json=payload, timeout=20)

def show_button(chat_id):
    kb = {"keyboard": [[{"text": BTN_CLIENT}]], "resize_keyboard": True, "one_time_keyboard": False}
    send_tg(chat_id, "Нажмите кнопку, чтобы начать общение с ассистентом GlobalNet.", reply_markup=kb)

def ask_agent(text, chat_id):
    headers = {"Content-Type": "application/json"}
    if AGENT_KEY:
        headers["Authorization"] = f"Bearer {AGENT_KEY}"
    r = requests.post(AGENT_URL, json={"session_id": str(chat_id), "message": text},
                      headers=headers, timeout=25)
    r.raise_for_status()
    data = r.json()
    return data.get("answer") or data.get("text") or "Не удалось получить ответ от агента."

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

    if not chat_id:
        return {"ok": True}

    # Старт/стоп
    if text == "/start":
        SESSIONS[chat_id] = {"active": False, "ts": time.time()}
        show_button(chat_id)
        return {"ok": True}

    if text == "/stop":
        SESSIONS.pop(chat_id, None)
        send_tg(chat_id, "Ассистент отключён. Нажмите /start, чтобы активировать кнопку.")
        return {"ok": True}

    # Активация клиентского режима только по кнопке
    if text == BTN_CLIENT:
        SESSIONS[chat_id] = {"active": True, "ts": time.time()}
        send_tg(chat_id, "Ассистент активирован. Задайте ваш вопрос.")
        return {"ok": True}

    # Если режим не активирован — показываем кнопку и выходим
    if not (SESSIONS.get(chat_id) or {}).get("active"):
        show_button(chat_id)
        return {"ok": True}

    # Любой текст здесь идёт в ИИ-агента
    try:
        answer = ask_agent(text, chat_id)
    except Exception as e:
        answer = f"Временная ошибка: {e}"

    send_tg(chat_id, answer)
    return {"ok": True}
