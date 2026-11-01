from flask import Flask

from config import Config
from extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from routes_batches import batches_bp
    from routes_documents import documents_bp
    from routes_review import review_bp

    app.register_blueprint(batches_bp, url_prefix="/api")
    app.register_blueprint(documents_bp, url_prefix="/api")
    app.register_blueprint(review_bp, url_prefix="/api")

    config_class.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        db.create_all()

    from celery_app import celery, init_celery

    init_celery(celery, app)

    return app
