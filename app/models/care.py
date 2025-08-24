from datetime import datetime, timezone

from ..extensions import db


class CareRequest(db.Model):
    __tablename__ = "care_requests"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    pet_id = db.Column(db.Integer, db.ForeignKey("pets.id"), nullable=True, index=True)

    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)

    location_text = db.Column(db.String(255))
    notes = db.Column(db.Text)

    status = db.Column(db.String(20), nullable=False, default="open")
    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    pet = db.relationship("Pet", backref=db.backref("care_requests", lazy="dynamic"))

    owner = db.relationship("User", backref="care_requests")
