from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os

# =========================
# ENV VARIABLES (Railway)
# =========================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================
# APP
# =========================
app = FastAPI()

# =========================
# OPENAI
# =========================
def ask_openai(user_text: str) -> str:
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a helpful WhatsApp assistant."},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.7,
            },
            timeout=15,
        )

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except Exception as e:
        print("OpenAI error:", e)
        return "Sorry, I had an error processing your message."


# =========================
# SEND WHATSAPP MESSAGE
# =========================
def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)
    print("WhatsApp response:", response.status_code, response.text)


# =========================
# WEBHOOK (POST)
# =========================
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        # 🔹 IGNORE STATUS / UPDATES
        if "messages" not in value:
            print("Evento sin mensaje (status/update)")
            return JSONResponse(content={"status": "ignored"})

        message = value["messages"][0]
        from_number = message["from"]
        user_text = message.get("text", {}).get("body", "")

        print("Mensaje recibido:", user_text)

        ai_response = ask_openai(user_text)
        send_whatsapp_message(from_number, ai_response)

    except Exception as e:
        print("Webhook error:", e)

    return JSONResponse(content={"status": "received"})


# =========================
# WEBHOOK VERIFY (GET)
# =========================
@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified")
        return int(challenge)

    return JSONResponse(content={"error": "Verification failed"}, status_code=403)
