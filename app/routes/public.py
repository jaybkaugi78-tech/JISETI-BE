from math import radians, sin, cos, sqrt, atan2

from flask import Blueprint, jsonify, request

from app.models import Report


public_bp = Blueprint("public", __name__)

VISIBLE_STATUSES = ["UNDER INVESTIGATION", "RESOLVED"]


@public_bp.get("/reports")
def public_reports():
    reports = (
        Report.query.filter(Report.status.in_(VISIBLE_STATUSES))
        .order_by(Report.created_at.desc())
        .all()
    )

    return jsonify({
        "reports": [report.to_dict() for report in reports]
    })


def calculate_distance_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    difference_lat = lat2 - lat1
    difference_lon = lon2 - lon1

    a = (
        sin(difference_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(difference_lon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c


@public_bp.get("/reports/nearby")
def nearby_reports():
    try:
        user_latitude = float(request.args.get("lat"))
        user_longitude = float(request.args.get("lng"))
        radius = float(request.args.get("radius", 10))
    except (TypeError, ValueError):
        return jsonify({
            "error": "lat and lng must be valid numbers"
        }), 400

    if radius <= 0:
        return jsonify({
            "error": "radius must be greater than 0"
        }), 400

    reports = (
        Report.query.filter(
            Report.status.in_(VISIBLE_STATUSES),
            Report.latitude.isnot(None),
            Report.longitude.isnot(None),
        )
        .order_by(Report.created_at.desc())
        .all()
    )

    nearby = []

    for report in reports:
        distance = calculate_distance_km(
            user_latitude,
            user_longitude,
            report.latitude,
            report.longitude,
        )

        if distance <= radius:
            report_data = report.to_dict()
            report_data["distance_km"] = round(distance, 2)
            nearby.append(report_data)

    nearby.sort(key=lambda report: report["distance_km"])

    return jsonify({
        "center": {
            "latitude": user_latitude,
            "longitude": user_longitude,
        },
        "radius_km": radius,
        "count": len(nearby),
        "reports": nearby,
    })