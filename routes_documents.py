from flask import Blueprint, jsonify

from extensions import db
from models import Document, Finding

documents_bp = Blueprint("documents", __name__)


@documents_bp.get("/documents/<int:document_id>")
def get_document(document_id: int):
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"error": "Document not found", "code": "not_found"}), 404
    return jsonify(document.to_dict(include_findings=True))


@documents_bp.get("/documents/<int:document_id>/findings")
def list_document_findings(document_id: int):
    document = db.session.get(Document, document_id)
    if document is None:
        return jsonify({"error": "Document not found", "code": "not_found"}), 404

    findings = Finding.query.filter_by(document_id=document_id).order_by(Finding.id).all()
    return jsonify({"document_id": document_id, "findings": [f.to_dict() for f in findings]})
