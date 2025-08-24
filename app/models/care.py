from datetime import datetime, timezone
from sqlalchemy import CheckConstraint
from ..extensions import db


class CareRequest(db.Model):
    __tablename__ = "care_requests"

    id = db.Column(db.Integer, primary_key=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pet_id = db.Column(
        db.Integer,
        db.ForeignKey("pets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # за MVP пазим naive datetime и ги третираме като UTC
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)

    location_text = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.String(20), nullable=False, default="open"
    )  # open, matched, confirmed, cancelled, completed
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_care_end_after_start"),
    )
