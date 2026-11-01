import enum
from datetime import datetime, timezone

from sqlalchemy import func

from extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class BatchStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Batch(db.Model):
    __tablename__ = "batches"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow, nullable=False)
    variables = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(32), default=BatchStatus.PENDING.value, nullable=False)

    documents = db.relationship("Document", back_populates="batch", lazy="dynamic")

    def to_dict(self, include_counts=False):
        data = {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "variables": self.variables,
            "status": self.status,
        }
        if include_counts:
            doc_counts = (
                db.session.query(Document.status, func.count(Document.id))
                .filter(Document.batch_id == self.id)
                .group_by(Document.status)
                .all()
            )
            data["document_counts"] = {status: count for status, count in doc_counts}
            doc_ids = [
                row[0] for row in self.documents.with_entities(Document.id).all()
            ]
            if doc_ids:
                finding_counts = (
                    db.session.query(Finding.review_status, func.count(Finding.id))
                    .filter(Finding.document_id.in_(doc_ids))
                    .group_by(Finding.review_status)
                    .all()
                )
                data["finding_review_counts"] = {
                    status: count for status, count in finding_counts
                }
            else:
                data["finding_review_counts"] = {}
        return data


class Document(db.Model):
    __tablename__ = "documents"
    __table_args__ = (
        db.UniqueConstraint("batch_id", "filename", name="uq_document_batch_filename"),
    )

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=False, index=True)
    filename = db.Column(db.String(512), nullable=False)
    storage_path = db.Column(db.String(1024), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), default=DocumentStatus.PENDING.value, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    idempotency_key = db.Column(db.String(128), nullable=False, unique=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)

    batch = db.relationship("Batch", back_populates="documents")
    findings = db.relationship("Finding", back_populates="document", lazy="dynamic")

    def to_dict(self, include_findings=False):
        data = {
            "id": self.id,
            "batch_id": self.batch_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }
        if include_findings:
            data["findings"] = [f.to_dict() for f in self.findings.all()]
        return data


class Finding(db.Model):
    __tablename__ = "findings"
    __table_args__ = (
        db.UniqueConstraint("document_id", "variable_name", name="uq_finding_document_variable"),
    )

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=False, index=True)
    variable_name = db.Column(db.String(256), nullable=False)
    extracted_value = db.Column(db.Text, nullable=False)
    review_status = db.Column(
        db.String(32), default=ReviewStatus.PENDING.value, nullable=False
    )
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    document = db.relationship("Document", back_populates="findings")

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "variable_name": self.variable_name,
            "extracted_value": self.extracted_value,
            "review_status": self.review_status,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
