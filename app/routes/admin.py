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


@admin_bp.get("/reports/<int:report_id>")
@jwt_required()
def get_report(report_id):
    user = get_admin()

    if not user or not user.is_admin:
        return jsonify({
            "error": "admin access required"
        }), 403

    report = db.session.get(
        Report,
        report_id
    )

    if not report:
        return jsonify({
            "error": "report not found"
        }), 404

    data = report.to_dict()

    data["status_history"] = [
        history.to_dict()
        for history in report.status_history
    ]

    return jsonify({
        "report": data
    }), 200


@admin_bp.patch("/reports/<int:report_id>/status")
@jwt_required()
def change_status(report_id):
    user = get_admin()

    if not user or not user.is_admin:
        return jsonify({
            "error": "admin access required"
        }), 403

    report = db.session.get(
        Report,
        report_id
    )

    if not report:
        return jsonify({
            "error": "report not found"
        }), 404

    data = request.get_json() or {}

    new_status = (
        data.get("status") or ""
    ).upper()

    if new_status not in VALID_STATUSES:
        return jsonify({
            "error": "invalid status"
        }), 400

    old_status = report.status

    if old_status == new_status:
        return jsonify({
            "message": "report already has this status",
            "report": report.to_dict(),
        }), 200

    report.status = new_status

    history = StatusHistory(
        report_id=report.id,
        old_status=old_status,
        new_status=new_status,
    )

    db.session.add(history)
    db.session.commit()

    updated_report = report.to_dict()

    updated_report["status_history"] = [
        item.to_dict()
        for item in report.status_history
    ]

    return jsonify({
        "message": "status updated",
        "report": updated_report,
    }), 200