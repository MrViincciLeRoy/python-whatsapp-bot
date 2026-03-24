import logging
import json

from flask import Blueprint, request, jsonify, current_app, render_template

from .decorators.security import signature_required
from .utils.whatsapp_utils import process_whatsapp_message, is_valid_whatsapp_message

webhook_blueprint = Blueprint("webhook", __name__)


def is_duplicate(message_id):
    from app import db
    from app.models import ProcessedMessage
    exists = ProcessedMessage.query.filter_by(message_id=message_id).first()
    if exists:
        return True
    try:
        db.session.add(ProcessedMessage(message_id=message_id))
        db.session.commit()
        return False
    except Exception:
        db.session.rollback()
        return True


def handle_message():
    body = request.get_json()

    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            message_id = body["entry"][0]["changes"][0]["value"]["messages"][0].get("id")

            if message_id and is_duplicate(message_id):
                logging.info(f"Duplicate message {message_id} — skipping")
                return jsonify({"status": "ok"}), 200

            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"status": "error", "message": "Not a WhatsApp API event"}), 404
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400


def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()


@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()


@webhook_blueprint.route("/", methods=["GET"])
def health():
    return "OK", 200


@webhook_blueprint.route("/leads", methods=["GET"])
def leads_dashboard():
    from app.models import Lead
    leads = Lead.query.order_by(Lead.last_seen.desc()).all()
    return render_template("dashboard.html", leads=leads)
