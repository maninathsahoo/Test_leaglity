import io
import zipfile

import pytest

from application import create_app
from celery_app import celery
from config import TestConfig
from extensions import db


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    base = tmp_path_factory.mktemp("leegality")
    upload_root = base / "uploads"
    upload_root.mkdir()
    db_path = base / "test.db"

    class Config(TestConfig):
        UPLOAD_ROOT = upload_root
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    application = create_app(Config)
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True
    return application


@pytest.fixture(autouse=True)
def clean_database(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield
    with app.app_context():
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf
