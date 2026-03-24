import logging
import re
import json
import requests
from flask import current_app, jsonify
from app.services.groq_service import generate_response, get_history, save_history

SERVICES_MENU = (
    "🏦 *BHK Invest (PTY) LTD* — Perseverance, Integrity and Honour\n"
    "✅ *NO UPFRONT FEES — 100% RISK-FREE*\n\n"
    "Which service are you interested in?\n\n"
    "1️⃣  ITC Clearance\n"
    "2️⃣  Debt Review Removal\n"
    "3️⃣  Score Uplifting\n"
    "4️⃣  Removal of Paid Defaults\n"
    "5️⃣  Rescinding of Paid Judgments\n"
    "6️⃣  Property Finance\n"
    "7️⃣  Vehicle Finance\n"
    "8️⃣  I'm not sure — help me choose\n\n"
    "_(Reply with a number 1–8)_"
)

SERVICE_MAP = {
    "1": "ITC Clearance",
    "2": "Debt Review Removal",
    "3": "Score Uplifting",
    "4": "Removal of Paid Defaults",
    "5": "Rescinding of Paid Judgments",
    "6": "Property Finance",
    "7": "Vehicle Finance",
    "8": None,
}

SERVICE_RESPONSES = {
    "ITC Clearance": (
        "✅ *ITC Clearance* — We remove negative listings and adverse information from your credit bureau profile.\n\n"
        "This means you can qualify for loans, bonds, and other financial products again. "
        "We have a *100% success rate* and have helped *580+ clients* just like you.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Are you currently blacklisted or do you have a judgment on your name?"
    ),
    "Debt Review Removal": (
        "✅ *Debt Review Removal* — We help you exit debt counselling legally and obtain your clearance certificate.\n\n"
        "Once cleared, you can access credit again and move forward financially.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Are all your accounts under debt review fully paid up?"
    ),
    "Score Uplifting": (
        "✅ *Score Uplifting* — We work to improve your credit score so you qualify for better financial products and lower interest rates.\n\n"
        "A better credit score opens doors — bonds, vehicle finance, personal loans and more.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Do you know your current credit score, or have you been declined for credit recently?"
    ),
    "Removal of Paid Defaults": (
        "✅ *Removal of Paid Defaults* — Even after you've paid a debt, the default listing can stay on your profile. We get it removed.\n\n"
        "This cleans up your credit record and improves your ability to access finance.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Do you have an idea of how many paid defaults are on your profile?"
    ),
    "Rescinding of Paid Judgments": (
        "✅ *Rescinding of Paid Judgments* — If you've paid a judgment but it's still showing on your credit record, we can have it rescinded (removed) legally.\n\n"
        "This is an important step to fully restoring your creditworthiness.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Do you have a copy of the judgment or the proof of payment?"
    ),
    "Property Finance": (
        "✅ *Property Finance* — We assist you in securing a home loan (1st or 2nd bond), even if you've been declined before.\n\n"
        "Our mission is to rehabilitate blacklisted clients and help them obtain a bond after successful clearance.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Are you looking to buy your first home, or have you been declined for a bond recently?"
    ),
    "Vehicle Finance": (
        "✅ *Vehicle Finance* — We help clients obtain vehicle finance even with a poor credit history.\n\n"
        "We work to clear your profile first so you can qualify for the best possible deal.\n\n"
        "🚀 No upfront fees. 100% risk-free.\n\n"
        "Apply here 👉 https://bhkinvest.co.za/apply\n"
        "Or call us: *012 002 5096*\n\n"
        "Have you been declined for vehicle finance recently, or is this your first application?"
    ),
}

NOT_SURE_RESPONSE = (
    "No problem! I'm here to help you figure out the right service. 😊\n\n"
    "Tell me a bit about your situation:\n\n"
    "• Are you blacklisted or have judgments on your name?\n"
    "• Are you under debt review?\n"
    "• Have you been declined for a home loan or vehicle finance?\n"
    "• Do you have paid defaults still showing on your profile?\n\n"
    "Just describe what's going on and I'll point you to the right solution. "
    "Remember — *no upfront fees and 100% risk-free*! 🚀"
)


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
    return lead and lead.name and lead.phone and lead.interest


def send_onboarding_message(wa_id, whatsapp_name):
    phone_display = f"+{wa_id}"
    msg = (
        f"👋 Hi {whatsapp_name}! Welcome to *BHKA Bot* — your BHK Invest assistant.\n\n"
        f"✅ *NO UPFRONT FEES | 100% RISK-FREE*\n\n"
        f"Before we start, let's confirm your details.\n\n"
        f"Is *{phone_display}* your contact number?\n\n"
        f"1️⃣  Yes, that's my number\n"
        f"2️⃣  No, I have a different number\n\n"
        f"_(Reply with 1 or 2)_"
    )
    send_message(get_text_message_input(wa_id, msg))


def send_name_request(wa_id):
    send_message(get_text_message_input(wa_id, "✏️ What's your *full name*?\n\nJust type it below 👇"))


def send_service_menu(wa_id):
    send_message(get_text_message_input(wa_id, SERVICES_MENU))


def send_email_consent(wa_id, name, service):
    msg = (
        f"✅ Great choice, *{name}*!\n\n"
        f"Would you like us to send you a follow-up email with more info about *{service}*?\n\n"
        f"1️⃣  Yes, send me an email\n"
        f"2️⃣  No thanks\n\n"
        f"_(Reply with 1 or 2)_"
    )
    send_message(get_text_message_input(wa_id, msg))


def handle_onboarding(wa_id, whatsapp_name, message_body):
    from app import db
    from app.models import Lead

    history = get_history(wa_id)
    step = next(
        (h["content"] for h in reversed(history) if h["role"] == "system" and h["content"].startswith("ONBOARDING_STEP:")),
        None
    )

    lead = Lead.query.filter_by(wa_id=wa_id).first()
    if not lead:
        lead = Lead(wa_id=wa_id)
        db.session.add(lead)
        db.session.commit()

    if step is None:
        history.append({"role": "system", "content": "ONBOARDING_STEP:phone"})
        save_history(wa_id, history)
        send_onboarding_message(wa_id, whatsapp_name)
        return True

    if step == "ONBOARDING_STEP:phone":
        if message_body.strip() == "1":
            lead.phone = f"+{wa_id}"
            db.session.commit()
        history.append({"role": "system", "content": "ONBOARDING_STEP:name"})
        save_history(wa_id, history)
        send_name_request(wa_id)
        return True

    if step == "ONBOARDING_STEP:name":
        lead.name = message_body.strip()
        db.session.commit()
        history.append({"role": "system", "content": "ONBOARDING_STEP:service_menu"})
        save_history(wa_id, history)
        send_service_menu(wa_id)
        return True

    if step == "ONBOARDING_STEP:service_menu":
        choice = message_body.strip()
        if choice not in SERVICE_MAP:
            send_message(get_text_message_input(wa_id, "Please reply with a number between *1 and 8* 😊\n\n"))
            send_service_menu(wa_id)
            return True

        service = SERVICE_MAP[choice]
        if service:
            lead.interest = service
            db.session.commit()
            reply = SERVICE_RESPONSES[service]
        else:
            reply = NOT_SURE_RESPONSE

        history.append({"role": "assistant", "content": reply})
        history.append({"role": "system", "content": "ONBOARDING_STEP:email_consent"})
        save_history(wa_id, history)
        send_message(get_text_message_input(wa_id, reply))
        send_email_consent(wa_id, lead.name, service or "our services")
        return True

    if step == "ONBOARDING_STEP:email_consent":
        if message_body.strip() == "1":
            history.append({"role": "system", "content": "ONBOARDING_STEP:email_capture"})
            save_history(wa_id, history)
            send_message(get_text_message_input(wa_id, "📧 What's your *email address*?\n\nJust type it below 👇"))
        else:
            history.append({"role": "system", "content": "ONBOARDING_STEP:done"})
            save_history(wa_id, history)
            send_message(get_text_message_input(
                wa_id,
                f"No problem, *{lead.name}*! Feel free to keep chatting or reach us anytime 😊\n\n"
                f"📞 *012 002 5096*\n🌐 https://bhkinvest.co.za/apply"
            ))
        return True

    if step == "ONBOARDING_STEP:email_capture":
        email = message_body.strip()
        lead.email = email
        db.session.commit()
        history.append({"role": "system", "content": "ONBOARDING_STEP:done"})
        save_history(wa_id, history)

        from app.services.email_service import send_lead_followup, send_new_lead_alert
        send_lead_followup(lead.name, email, lead.interest)
        send_new_lead_alert(lead.name, lead.phone, email, lead.interest)

        send_message(get_text_message_input(
            wa_id,
            f"✅ Done! We've sent a follow-up email to *{email}*.\n\n"
            f"Feel free to keep chatting or call us on *012 002 5096* 😊"
        ))
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
    send_message(get_text_message_input(wa_id, response))


def is_valid_whatsapp_message(body):
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )
