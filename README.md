# Leegality Contract Batch Processor

All project files live in this single folder (flat layout).

Flask API for bulk contract ZIP uploads, asynchronous mock extraction (Celery + Redis), and human review of extracted variables.

## Prerequisites

- Python 3.9+
- Redis (for background workers; optional in tests)
- PostgreSQL (optional; SQLite used by default)

## Quick start

```bash
cd Test_legality
python3 -m venv .venv          # skip if .venv already exists
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

If you see `ModuleNotFoundError: No module named 'flask'`, the active environment does not have dependencies installed—activate `.venv` above (or run `pip install -r requirements.txt` in your `(leagal)` conda env).

```bash
# optional infra (requires Docker Desktop running)

docker compose up -d

export DATABASE_URL=postgresql://leegality:leegality@localhost:5432/leegality
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Terminal 1 — API:

```bash
python wsgi.py
```

Terminal 2 — worker:

```bash
celery -A celery_app worker --loglevel=info
```

## API usage

```bash
curl -X POST http://127.0.0.1:5000/api/batches \
  -F 'file=@contracts.zip' \
  -F 'variables=["effective_date","monthly_rent","governing_law"]'

curl http://127.0.0.1:5000/api/batches/1
curl http://127.0.0.1:5000/api/batches/1/documents
curl http://127.0.0.1:5000/api/documents/1
curl -X PATCH http://127.0.0.1:5000/api/findings/1 \
  -H 'Content-Type: application/json' \
  -d '{"review_status":"accepted"}'
```

## Tests

```bash
pytest
```

## Key modules (same directory)

| File | Role |
|------|------|
| `application.py` | Flask app factory |
| `routes_*.py` | REST endpoints |
| `zip_ingest.py` | ZIP validation and extract |
| `mock_extractor.py` | Mock extraction API |
| `extraction.py` | Celery `process_document` |
| `batch_status.py` | Batch status derivation |
| `models.py` | SQLAlchemy models |
| `DESIGN.md` | Architecture and future scope |
| `PRODUCTION_INCIDENTS.md` | Part 2 case study |

See `DESIGN.md` for assumptions, trade-offs, and limitations.
