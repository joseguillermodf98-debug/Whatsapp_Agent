from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os
import re

# =========================
# ENV VARIABLES (Railway)
# =========================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# =========================
# OPENAI ASSISTANT
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
        print(f"Error en OpenAI: {e}")
        return "Lo siento, tuve un error al procesar tu mensaje."

# =========================
# SEND WHATSAPP MESSAGE
# =========================
def send_whatsapp_message(to_number: str, text: str):
    # Limpieza crucial: eliminamos cualquier símbolo '+' o espacios
    clean_number = re.sub(r'\D', '', to_number)
    
    # IMPORTANTE: Si tu número de prueba en Meta NO tiene el "1" después del "52", 
    # y el webhook te lo manda con "1", lo quitamos aquí:
    if clean_number.startswith("521"):
        clean_number = "52" + clean_number[3:]

    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": clean_number,
        "type": "text",
        "text": {"body": text},
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers)
    print(f"Enviando a: {clean_number}")
    print(f"WhatsApp response: {response.status_code} {response.text}")

# =========================
# WEBHOOK (POST)
# =========================
@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    try:
        data = await request.json()
        
        # Extraemos la estructura de Meta
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        if "messages" not in value:
            print("Evento de estado (sent/delivered/read) ignorado.")
            return JSONResponse(content={"status": "ignored"})

        message = value["messages"][0]
        from_number = message["from"]
        user_text = message.get("text", {}).get("body", "")

        print(f"Mensaje recibido de {from_number}: {user_text}")

        # Procesamos con IA y respondemos
        ai_response = ask_openai(user_text)
        send_whatsapp_message(from_number, ai_response)

    except Exception as e:
        print(f"Error en Webhook: {e}")

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
        print("Webhook verificado correctamente.")
        return int(challenge)

    return JSONResponse(content={"error": "Fallo de verificación"}, status_code=403)
