from datetime import datetime, timezone
from app.extensions import db


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    type = db.Column(
        db.String(30),
        nullable=False
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=False
    )

    status = db.Column(
        db.String(30),
        default="DRAFT",
        nullable=False
    )

    location_name = db.Column(
        db.String(255)
    )

    latitude = db.Column(
        db.Float
    )

    longitude = db.Column(
        db.Float
    )

    # Uploaded images/videos
    media = db.Column(
        db.JSON,
        nullable=False,
        default=list
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    status_history = db.relationship(
        "StatusHistory",
        backref="report",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "media": self.media or [],
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }