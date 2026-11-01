import json

from flask import Blueprint, jsonify, request

from batch_status import recompute_batch_status
from extensions import db
from extraction import process_document
from models import Batch, Document
from zip_ingest import ZipValidationError, ingest_zip

batches_bp = Blueprint("batches", __name__)


@batches_bp.post("/batches")
def create_batch():
    if "file" not in request.files:
        return jsonify({"error": "Missing ZIP file", "code": "missing_file"}), 400

    variables_raw = request.form.get("variables")
    if not variables_raw:
        return jsonify({"error": "Missing variables field", "code": "missing_variables"}), 400

    try:
        variables = json.loads(variables_raw)
    except json.JSONDecodeError:
        return jsonify({"error": "variables must be valid JSON array", "code": "invalid_variables"}), 400

    if not isinstance(variables, list) or not all(isinstance(v, str) for v in variables):
        return jsonify({"error": "variables must be a JSON array of strings", "code": "invalid_variables"}), 400

    zip_file = request.files["file"]
    if not zip_file.filename:
        return jsonify({"error": "Empty filename", "code": "missing_file"}), 400

    try:
        batch = ingest_zip(zip_file, variables)
    except ZipValidationError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc), "code": exc.code}), 400

    documents = Document.query.filter_by(batch_id=batch.id).all()
    for doc in documents:
        process_document.delay(doc.id)

    recompute_batch_status(batch.id)
    db.session.refresh(batch)

    return jsonify(batch.to_dict(include_counts=True)), 202


@batches_bp.get("/batches/<int:batch_id>")
def get_batch(batch_id: int):
    batch = db.session.get(Batch, batch_id)
    if batch is None:
        return jsonify({"error": "Batch not found", "code": "not_found"}), 404
    return jsonify(batch.to_dict(include_counts=True))


@batches_bp.get("/batches/<int:batch_id>/documents")
def list_batch_documents(batch_id: int):
    batch = db.session.get(Batch, batch_id)
    if batch is None:
        return jsonify({"error": "Batch not found", "code": "not_found"}), 404

    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 50)), 1), 200)

    pagination = (
        Document.query.filter_by(batch_id=batch_id)
        .order_by(Document.id)
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return jsonify(
        {
            "batch_id": batch_id,
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "documents": [d.to_dict() for d in pagination.items],
        }
    )
