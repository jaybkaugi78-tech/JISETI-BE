from datetime import datetime, timezone
from app.extensions import db


class StatusHistory(db.Model):
    __tablename__ = "status_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    report_id = db.Column(
        db.Integer,
        db.ForeignKey("reports.id"),
        nullable=False
    )

    old_status = db.Column(
        db.String(30),
        nullable=False
    )

    new_status = db.Column(
        db.String(30),
        nullable=False
    )

    changed_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_at": (
                self.changed_at.isoformat()
                if self.changed_at
                else None
            ),
            "is_read": self.is_read,
        }