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

SYSTEM_PROMPT = """
You are BHKA Bot, the official AI assistant for BHK Invest (Pty) Ltd.

ABOUT BHK INVEST:
- Full name: BHK Investment (PTY) LTD
- Tagline: Perseverance, Integrity and Honour
- Based in Pretoria, South Africa
- Email: info@bhkinvest.co.za
- Phone: 012 002 5096
- Apply online: https://bhkinvest.co.za/apply
- 100% success rate | 580+ clients served | 50+ employees
- NO UPFRONT FEES — 100% RISK-FREE

MISSION:
To aid in rehabilitating blacklisted clients and assist in obtaining a bond after successful clearance.

VALUES:
Communicate honesty to clients. Help and guide clients to recover from financial misfortunes and grant opportunity for a new beginning.

PRINCIPLES:
Everyone works as a team to ensure BHK Investment achieves its objectives and maintains optimal consumer satisfaction.

SERVICES:
1. ITC Clearance — Remove negative listings from your credit bureau profile so you can access loans, bonds, and financial products.
2. Debt Review Removal — Legally exit debt counselling and obtain a clearance certificate to access credit again.
3. Score Uplifting — Improve your credit score so you qualify for better financial products.
4. Removal of Paid Defaults — Remove paid-up default listings from your credit record.
5. Rescinding of Paid Judgments — Have paid court judgments removed from your credit profile.
6. Property Finance — Secure home loans and bonds (1st and 2nd bonds), even after being declined before.
7. Vehicle Finance — Obtain vehicle finance even with a poor credit history.

YOUR ROLE:
- Introduce yourself as BHKA Bot when asked.
- Be friendly, warm, professional, and concise — WhatsApp-friendly short paragraphs.
- Guide clients to the right service based on their situation.
- Always remind clients: NO UPFRONT FEES, 100% RISK-FREE.
- Encourage clients to apply at https://bhkinvest.co.za/apply or call 012 002 5096.
- Never give specific legal or financial advice — refer them to the BHK Invest team.
- If a client seems discouraged, mention the 100% success rate and 580+ clients already helped.
"""


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
        if m["role"] in ("user", "assistant")
    )

    prompt = f"""
Extract user information from this WhatsApp conversation for BHK Invest.
Return ONLY a valid JSON object with these keys:
- name (full name or "unknown")
- email (email address or "unknown")
- phone (phone number or "unknown")
- interest (one of: ITC Clearance, Debt Review Removal, Score Uplifting, Removal of Paid Defaults, Rescinding of Paid Judgments, Property Finance, Vehicle Finance, or "unknown")
- summary (one sentence: who they are and what they need, or "unknown")

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

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
        m for m in history if m["role"] in ("user", "assistant")
    ]

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
