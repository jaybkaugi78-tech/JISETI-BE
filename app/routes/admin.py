
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Report, StatusHistory, User
admin_bp = Blueprint("admin", __name__)

VALID_STATUSES = {
    "UNDER INVESTIGATION",
    "REJECTED",
    "RESOLVED",
}

def get_admin():
    return db.session.get(
        User,
        int(get_jwt_identity())
    )
@admin_bp.get("/reports")
@jwt_required()
def all_reports():
    user = get_admin()

    if not user or not user.is_admin:
        return jsonify({
            "error": "admin access required"
        }), 403

    query = Report.query

    status = request.args.get("status")

    if status:
        query = query.filter_by(
            status=status.upper()
        )

    report_type = request.args.get("type")

    if report_type:
        query = query.filter_by(
            type=report_type
            .upper()
            .replace("-", "_")
        )

    reports = (
        query
        .order_by(
            Report.created_at.desc()
        )
        .all()
    )

    return jsonify({
        "reports": [
            report.to_dict()
            for report in reports
        ]
    }), 200
