from flask import Flask, jsonify
from dotenv import load_dotenv

from .config import Config
from .extensions import db, jwt, cors
from .cloudinary_config import configure_cloudinary


def create_app():
    load_dotenv()

    configure_cloudinary()

    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    from .routes.auth import auth_bp
    from .routes.reports import reports_bp
    from .routes.admin import admin_bp
    from .routes.public import public_bp

    app.register_blueprint(
        auth_bp,
        url_prefix="/api/auth",
    )

    app.register_blueprint(
        reports_bp,
        url_prefix="/api/reports",
    )

    app.register_blueprint(
        admin_bp,
        url_prefix="/api/admin",
    )

    app.register_blueprint(
        public_bp,
        url_prefix="/api/public",
    )

    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "ok"
        })

    with app.app_context():
        from .models import (
            User,
            Report,
            StatusHistory,
        )

        db.create_all()

    return app