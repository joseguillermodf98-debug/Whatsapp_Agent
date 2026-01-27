import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "WhatsApp Agent running"}

def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=payload)

def ask_openai(prompt: str) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful WhatsApp assistant."},
                {"role": "user", "content": prompt}
            ]
        }
    )
    return response.json()["choices"][0]["message"]["content"]

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = message["from"]
        user_text = message["text"]["body"]

        ai_response = ask_openai(user_text)
        send_whatsapp_message(from_number, ai_response)

    except Exception as e:
        print("Error:", e)

    return JSONResponse(content={"status": "received"})

@app.get("/webhook")
def verify_webhook(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None
):
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)

    return JSONResponse(status_code=403, content={"error": "Verification failed"})
