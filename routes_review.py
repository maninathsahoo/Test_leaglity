from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from extensions import db
from models import Finding, ReviewStatus

review_bp = Blueprint("review", __name__)


@review_bp.patch("/findings/<int:finding_id>")
def review_finding(finding_id: int):
    finding = db.session.get(Finding, finding_id)
    if finding is None:
        return jsonify({"error": "Finding not found", "code": "not_found"}), 404

    body = request.get_json(silent=True) or {}
    review_status = body.get("review_status")
    if review_status not in (ReviewStatus.ACCEPTED.value, ReviewStatus.REJECTED.value):
        return jsonify(
            {
                "error": "review_status must be 'accepted' or 'rejected'",
                "code": "invalid_review_status",
            }
        ), 400

    finding.review_status = review_status
    finding.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(finding.to_dict())
