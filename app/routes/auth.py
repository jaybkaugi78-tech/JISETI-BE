from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from app.extensions import db
from app.models import User
@auth_bp.post("/register")
def register():
    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({
            "error": "username, email and password are required"
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "error": "email already registered"
        }), 409

    user = User(
        username=username,
        email=email
    )

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "access_token": create_access_token(
            identity=str(user.id)
        ),
        "user": user.to_dict()
    }), 201
@auth_bp.post("/login")
def login():
    data = request.get_json() or {}

    user = User.query.filter_by(
        email=(data.get("email") or "").strip().lower()
    ).first()

    if not user or not user.check_password(
        data.get("password") or ""
    ):
        return jsonify({
            "error": "invalid email or password"
        }), 401

    return jsonify({
        "access_token": create_access_token(
            identity=str(user.id)
        ),
        "user": user.to_dict()
    })
@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(
        User,
        int(get_jwt_identity())
    )

    if not user:
        return jsonify({
            "error": "user not found"
        }), 404

    return jsonify({
        "user": user.to_dict()
    })
