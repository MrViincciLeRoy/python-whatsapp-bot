import os
import itertools
import shelve
from groq import Groq

_keys = [k for k in [
    os.getenv("GROQ_KEY_1"),
    os.getenv("GROQ_KEY_2"),
    os.getenv("GROQ_KEY_3"),
] if k]

_key_cycle = itertools.cycle(_keys)

def get_client():
    return Groq(api_key=next(_key_cycle))

def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as shelf:
        return shelf.get(wa_id, [])

def store_thread(wa_id, history):
    with shelve.open("threads_db", writeback=True) as shelf:
        shelf[wa_id] = history

def generate_response(message_body, wa_id, name):
    history = check_if_thread_exists(wa_id)

    history.append({"role": "user", "content": message_body})

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful business assistant. "
                "Be professional, friendly, and concise. "
                "If someone seems interested in services, capture their interest warmly."
            )
        }
    ] + history

    model = os.getenv("GROQ_MODEL", "llama3-70b-8192")
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
            store_thread(wa_id, history)
            return reply
        except Exception as e:
            if attempt == max_retries - 1:
                return "Sorry, I'm having trouble responding right now. Please try again shortly."￼Enter
