import os
import json
import logging
import itertools
from groq import Groq

_keys = [k for k in [
    os.getenv("GROQ_KEY_1"),
    os.getenv("GROQ_KEY_2"),
    os.getenv("GROQ_KEY_3"),
] if k]

_key_cycle = itertools.cycle(_keys)


def get_client():
    return Groq(api_key=next(_key_cycle))


def get_history(wa_id):
    from app import db
    from app.models import Conversation
    convo = Conversation.query.filter_by(wa_id=wa_id).first()
    return convo.get_history() if convo else []


def save_history(wa_id, history):
    from app import db
    from app.models import Conversation
    convo = Conversation.query.filter_by(wa_id=wa_id).first()
    if not convo:
        convo = Conversation(wa_id=wa_id)
        db.session.add(convo)
    convo.set_history(history)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to save conversation for {wa_id}: {e}")


def extract_lead_info(history):
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    client = get_client()

    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    )

    prompt = f"""
Extract user information from the conversation below.
Return ONLY a valid JSON object with these keys:
- name (full name or "unknown")
- email (email address or "unknown")
- phone (phone number or "unknown")
- interest (ANY product, service, topic, or problem they mentioned — be liberal, grab anything relevant, or "unknown")
- summary (one sentence: who they are and what they want, or "unknown")

Conversation:
{conversation_text}

Respond ONLY with the JSON object, no other text.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        logging.error(f"Lead extraction failed: {e}")
        return {}


def generate_response(message_body, wa_id, name):
    history = get_history(wa_id)
    history.append({"role": "user", "content": message_body})

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful business assistant. "
                "Be professional, friendly, and concise. "
                "You have memory of the full conversation history provided. "
                "Always refer back to what the user has already told you. "
                "Your goal is to understand what the person needs and capture their interest. "
                "Always ask what they are looking for or what service/product they need. "
                "Once you know, confirm their interest clearly in your reply."
            )
        }
    ] + history

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    max_retries = len(_keys)

    for attempt in range(max_retries):
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            reply = response.choices[0].message.content.strip()
            history.append({"role": "assistant", "content": reply})
            save_history(wa_id, history)

            extracted = extract_lead_info(history)
            if extracted:
                from app.services.lead_service import upsert_lead
                upsert_lead(wa_id, extracted)

            return reply
        except Exception as e:
            logging.error(f"Groq attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                return "Sorry, I'm having trouble responding right now. Please try again shortly."
