from extensions import db
from models import Batch, BatchStatus, Document, DocumentStatus


def recompute_batch_status(batch_id: int) -> None:
    batch = db.session.get(Batch, batch_id)
    if batch is None:
        return
    if batch.status == BatchStatus.FAILED.value:
        return

    statuses = [
        row[0]
        for row in db.session.query(Document.status)
        .filter(Document.batch_id == batch_id)
        .all()
    ]
    if not statuses:
        batch.status = BatchStatus.FAILED.value
        db.session.commit()
        return

    if any(s in (DocumentStatus.PENDING.value, DocumentStatus.PROCESSING.value) for s in statuses):
        batch.status = BatchStatus.PROCESSING.value
    elif all(s == DocumentStatus.COMPLETED.value for s in statuses):
        batch.status = BatchStatus.COMPLETED.value
    elif all(s in (DocumentStatus.COMPLETED.value, DocumentStatus.FAILED.value) for s in statuses):
        batch.status = BatchStatus.COMPLETED_WITH_ERRORS.value
    else:
        batch.status = BatchStatus.PROCESSING.value

    db.session.commit()
