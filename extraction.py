from datetime import datetime, timezone

import mock_extractor
from batch_status import recompute_batch_status
from celery_app import celery
from extensions import db
from models import Document, DocumentStatus, Finding, ReviewStatus


def _utcnow():
    return datetime.now(timezone.utc)


@celery.task(name="extraction.process_document", bind=True, max_retries=2)
def process_document(self, document_id: int):
    document = db.session.get(Document, document_id)
    if document is None:
        return {"error": "document_not_found"}

    if document.status == DocumentStatus.COMPLETED.value:
        return {"status": "already_completed", "document_id": document_id}

    existing_findings = document.findings.count()
    if existing_findings > 0:
        document.status = DocumentStatus.COMPLETED.value
        if not document.finished_at:
            document.finished_at = _utcnow()
        db.session.commit()
        recompute_batch_status(document.batch_id)
        return {"status": "already_completed", "document_id": document_id}

    batch = document.batch
    variables = batch.variables or []

    document.status = DocumentStatus.PROCESSING.value
    document.started_at = _utcnow()
    document.error_message = None
    db.session.commit()

    try:
        values = mock_extractor.extract(document.storage_path, variables)

        for var, value in values.items():
            finding = Finding(
                document_id=document.id,
                variable_name=var,
                extracted_value=value,
                review_status=ReviewStatus.PENDING.value,
            )
            db.session.add(finding)

        document.status = DocumentStatus.COMPLETED.value
        document.finished_at = _utcnow()
        db.session.commit()

    except mock_extractor.MockExtractionTimeout as exc:
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(exc)
        document.finished_at = _utcnow()
        db.session.commit()
        recompute_batch_status(document.batch_id)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

    except mock_extractor.MockExtractionFailure as exc:
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(exc)
        document.finished_at = _utcnow()
        db.session.commit()
        recompute_batch_status(document.batch_id)
        return {"status": "failed", "document_id": document_id}

    except Exception as exc:
        document.status = DocumentStatus.FAILED.value
        document.error_message = str(exc)
        document.finished_at = _utcnow()
        db.session.commit()
        recompute_batch_status(document.batch_id)
        raise

    recompute_batch_status(document.batch_id)
    return {"status": "completed", "document_id": document_id}
