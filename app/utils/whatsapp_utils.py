import logging
from flask import current_app, jsonify
import json
import requests
from app.services.groq_service import generate_response, get_history, save_history
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    })


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    text = re.sub(r"\【.*?\】", "", text).strip()
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    return text


def is_onboarded(wa_id):
    from app.models import Lead
    lead = Lead.query.filter_by(wa_id=wa_id).first()
    return lead and lead.name and lead.email


def send_onboarding_message(wa_id, whatsapp_name):
    phone_display = f"+{wa_id}"
    msg = (
        f"👋 Hey {whatsapp_name}! Welcome!\n\n"
        f"Before we get started, I'd love to know a bit more about you. "
        f"Just reply with the number of your choice:\n\n"
        f"1️⃣  Yes, use *{phone_display}* as my contact number\n"
        f"2️⃣  No, I have a different number\n\n"
        f"_(This helps us keep your details accurate)_"
    )
    data = get_text_message_input(wa_id, msg)
    send_message(data)


def send_name_request(wa_id):
    msg = (
        "✏️ What's your *full name*?\n\n"
        "Just type it below 👇"
    )
    data = get_text_message_input(wa_id, msg)
    send_message(data)


def send_email_request(wa_id):
    msg = (
        "📧 What's your *email address*?\n\n"
        "Just type it below 👇"
    )
    data = get_text_message_input(wa_id, msg)
    send_message(data)


def send_welcome_complete(wa_id, name):
    msg = (
        f"✅ Perfect, *{name}*! You're all set.\n\n"
        f"How can I help you today? Feel free to ask me anything! 😊"
    )
    data = get_text_message_input(wa_id, msg)
    send_message(data)


def handle_onboarding(wa_id, whatsapp_name, message_body):
    from app import db
    from app.models import Lead

    history = get_history(wa_id)
    step = next((h["content"] for h in reversed(history) if h["role"] == "system" and h["content"].startswith("ONBOARDING_STEP:")), None)

    lead = Lead.query.filter_by(wa_id=wa_id).first()
    if not lead:
        lead = Lead(wa_id=wa_id)
        db.session.add(lead)
        db.session.commit()

    if step is None:
        # First time — ask about phone
        history.append({"role": "system", "content": "ONBOARDING_STEP:phone"})
        save_history(wa_id, history)
        send_onboarding_message(wa_id, whatsapp_name)
        return True

    if step == "ONBOARDING_STEP:phone":
        if message_body.strip() == "1":
            lead.phone = f"+{wa_id}"
        # If 2 or anything else, we skip phone for now
        db.session.commit()
        history.append({"role": "system", "content": "ONBOARDING_STEP:name"})
        save_history(wa_id, history)
        send_name_request(wa_id)
        return True

    if step == "ONBOARDING_STEP:name":
        lead.name = message_body.strip()
        db.session.commit()
        history.append({"role": "system", "content": "ONBOARDING_STEP:email"})
        save_history(wa_id, history)
        send_email_request(wa_id)
        return True

    if step == "ONBOARDING_STEP:email":
        lead.email = message_body.strip()
        db.session.commit()
        history.append({"role": "system", "content": "ONBOARDING_STEP:done"})
        save_history(wa_id, history)
        send_welcome_complete(wa_id, lead.name)
        return True

    return False


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]

    logging.info(f"Message from {name} ({wa_id}): {message_body}")

    if not is_onboarded(wa_id):
        handled = handle_onboarding(wa_id, name, message_body)
        if handled:
            return

    response = generate_response(message_body, wa_id, name)
    response = process_text_for_whatsapp(response)
    logging.info(f"Replying to {wa_id}: {response}")
    data = get_text_message_input(wa_id, response)
    send_message(data)


def is_valid_whatsapp_message(body):
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
