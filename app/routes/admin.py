
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
