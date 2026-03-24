from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import load_configurations, configure_logging

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    load_configurations(app)
    configure_logging()

    db.init_app(app)

    from .views import webhook_blueprint
    app.register_blueprint(webhook_blueprint)

    with app.app_context():
        from app import models
        db.create_all()

    return app
