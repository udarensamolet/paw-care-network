from datetime import datetime, timezone
from sqlalchemy import CheckConstraint
from ..extensions import db


class Pet(db.Model):
    __tablename__ = "pets"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(120), nullable=False)
    species = db.Column(db.String(50), nullable=True)
    breed = db.Column(db.String(120), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    care_instructions = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    photo_url = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        CheckConstraint("age IS NULL OR age >= 0", name="ck_pet_age_non_negative"),
    )