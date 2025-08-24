from datetime import datetime, timezone
from ..extensions import db


class CareOffer(db.Model):
    __tablename__ = "care_offers"

    id = db.Column(db.Integer, primary_key=True)

    care_request_id = db.Column(
        db.Integer,
        db.ForeignKey("care_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sitter_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(32), nullable=False, default="offered")

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )