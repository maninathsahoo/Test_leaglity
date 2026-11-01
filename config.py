import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'leegality.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_ROOT = Path(os.environ.get("UPLOAD_ROOT", BASE_DIR / "uploads"))
    MAX_DOCUMENTS_PER_ZIP = int(os.environ.get("MAX_DOCUMENTS_PER_ZIP", "1000"))
    MAX_DOCUMENT_BYTES = int(os.environ.get("MAX_DOCUMENT_BYTES", str(15 * 1024 * 1024)))
    ALLOWED_EXTENSIONS = frozenset(
        ext.strip().lower()
        for ext in os.environ.get("ALLOWED_EXTENSIONS", ".pdf,.txt,.docx").split(",")
    )

    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    MOCK_SLEEP_MIN = float(os.environ.get("MOCK_SLEEP_MIN", "0.01"))
    MOCK_SLEEP_MAX = float(os.environ.get("MOCK_SLEEP_MAX", "0.05"))
    MOCK_TIMEOUT_RATE = float(os.environ.get("MOCK_TIMEOUT_RATE", "0"))
    MOCK_FAIL_RATE = float(os.environ.get("MOCK_FAIL_RATE", "0"))
    MOCK_EXTRACT_TIMEOUT_SEC = float(os.environ.get("MOCK_EXTRACT_TIMEOUT_SEC", "30"))

    CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in (
        "1",
        "true",
        "yes",
    )


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_ROOT = BASE_DIR / "test_uploads"
    CELERY_TASK_ALWAYS_EAGER = True
    MOCK_SLEEP_MIN = 0
    MOCK_SLEEP_MAX = 0
    MOCK_TIMEOUT_RATE = 0
    MOCK_FAIL_RATE = 0
