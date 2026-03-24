import logging
from datetime import datetime
from app import db
from app.models import Lead


def upsert_lead(wa_id, extracted: dict):
    lead = Lead.query.filter_by(wa_id=wa_id).first()

    if not lead:
        lead = Lead(wa_id=wa_id)
        db.session.add(lead)

    if extracted.get("name") and extracted["name"] != "unknown":
        lead.name = extracted["name"]
    if extracted.get("email") and extracted["email"] != "unknown":
        lead.email = extracted["email"]
    if extracted.get("phone") and extracted["phone"] != "unknown":
        lead.phone = extracted["phone"]
    if extracted.get("interest") and extracted["interest"] != "unknown":
        lead.interest = extracted["interest"]
    if extracted.get("summary") and extracted["summary"] != "unknown":
        lead.summary = extracted["summary"]

    lead.last_seen = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to save lead {wa_id}: {e}")
