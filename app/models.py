from datetime import datetime
from app import db
import json


class Lead(db.Model):
    __tablename__ = "leads"

    id = db.Column(db.Integer, primary_key=True)
    wa_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    interest = db.Column(db.Text)
    summary = db.Column(db.Text)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Lead {self.wa_id} - {self.name}>"


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    wa_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    history_json = db.Column(db.Text, nullable=False, default="[]")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_history(self):
        return json.loads(self.history_json)

    def set_history(self, history):
        self.history_json = json.dumps(history)
