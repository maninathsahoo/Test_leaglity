import json

from conftest import make_zip
from extensions import db
from models import Batch, BatchStatus, Document, DocumentStatus, Finding, ReviewStatus


def test_create_batch_and_process(client, app):
    z = make_zip({"contract1.txt": b"hello", "contract2.txt": b"world"})
    resp = client.post(
        "/api/batches",
        data={
            "file": (z, "batch.zip"),
            "variables": json.dumps(["effective_date", "monthly_rent"]),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == BatchStatus.COMPLETED.value
    assert "document_counts" in data

    batch_id = data["id"]
    resp = client.get(f"/api/batches/{batch_id}/documents")
    assert resp.status_code == 200
    docs = resp.get_json()["documents"]
    assert len(docs) == 2
    assert all(d["status"] == DocumentStatus.COMPLETED.value for d in docs)


def test_get_document_with_findings(client):
    z = make_zip({"a.txt": b"content"})
    client.post(
        "/api/batches",
        data={
            "file": (z, "batch.zip"),
            "variables": json.dumps(["effective_date"]),
        },
        content_type="multipart/form-data",
    )
    with client.application.app_context():
        doc = Document.query.first()
        doc_id = doc.id

    resp = client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["findings"]) == 1
    assert body["findings"][0]["variable_name"] == "effective_date"


def test_review_finding_accept_reject(client):
    z = make_zip({"a.txt": b"content"})
    client.post(
        "/api/batches",
        data={
            "file": (z, "batch.zip"),
            "variables": json.dumps(["governing_law"]),
        },
        content_type="multipart/form-data",
    )
    with client.application.app_context():
        finding = Finding.query.first()
        finding_id = finding.id

    resp = client.patch(
        f"/api/findings/{finding_id}",
        json={"review_status": "accepted"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["review_status"] == ReviewStatus.ACCEPTED.value

    resp = client.patch(
        f"/api/findings/{finding_id}",
        json={"review_status": "rejected"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["review_status"] == ReviewStatus.REJECTED.value


def test_batch_completed_with_errors(client, app, monkeypatch):
    import mock_extractor

    def fail_extract(path, variables):
        raise mock_extractor.MockExtractionFailure("forced fail")

    monkeypatch.setattr(mock_extractor, "extract", fail_extract)

    z = make_zip({"ok.txt": b"1", "bad.txt": b"2"})
    resp = client.post(
        "/api/batches",
        data={
            "file": (z, "batch.zip"),
            "variables": json.dumps(["effective_date"]),
        },
        content_type="multipart/form-data",
    )
    assert resp.status_code == 202
    batch_id = resp.get_json()["id"]
    with app.app_context():
        batch = db.session.get(Batch, batch_id)
        assert batch.status == BatchStatus.COMPLETED_WITH_ERRORS.value


def test_idempotent_task_no_duplicate_findings(client, app):
    z = make_zip({"solo.txt": b"x"})
    client.post(
        "/api/batches",
        data={
            "file": (z, "batch.zip"),
            "variables": json.dumps(["expiry_date", "notice_period"]),
        },
        content_type="multipart/form-data",
    )
    with app.app_context():
        doc = Document.query.first()
        from extraction import process_document

        process_document.delay(doc.id)
        process_document.delay(doc.id)
        count = Finding.query.filter_by(document_id=doc.id).count()
        assert count == 2
