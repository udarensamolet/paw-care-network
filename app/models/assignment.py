from datetime import datetime, timezone

from sqlalchemy import CheckConstraint

from ..extensions import db


class CareAssignment(db.Model):
    __tablename__ = "care_assignments"

    id = db.Column(db.Integer, primary_key=True)

    care_request_id = db.Column(
        db.Integer, db.ForeignKey("care_requests.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    sitter_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    pet_id = db.Column(
        db.Integer, db.ForeignKey("pets.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    start_at = db.Column(db.DateTime, nullable=False)
    end_at   = db.Column(db.DateTime, nullable=False)

    sitter_note = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_assign_end_after_start"),
    )

    pet = db.relationship("Pet", backref=db.backref("assignments", lazy="dynamic"))
    care_request = db.relationship("CareRequest", backref=db.backref("assignments", lazy="dynamic"))
    sitter = db.relationship("User", foreign_keys=[sitter_id])