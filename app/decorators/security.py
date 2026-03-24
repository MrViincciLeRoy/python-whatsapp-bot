from functools import wraps
from flask import current_app, jsonify, request
import logging
import hashlib
import hmac


def validate_signature(payload, signature):
    expected_signature = hmac.new(
        bytes(current_app.config["APP_SECRET"], "latin-1"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def signature_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        signature = request.headers.get("X-Hub-Signature-256", "")[7:]
        payload = request.data.decode("utf-8")

        logging.info(f"=== SIGNATURE CHECK === sig={signature[:20]}... payload_len={len(payload)}")

        if not validate_signature(payload, signature):
            logging.info("=== SIGNATURE FAILED — request blocked ===")
            return jsonify({"status": "error", "message": "Invalid signature"}), 403

        logging.info("=== SIGNATURE PASSED ===")
        return f(*args, **kwargs)

    return decorated_function
