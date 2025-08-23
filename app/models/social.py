from datetime import datetime, timezone
from sqlalchemy import CheckConstraint, or_
from ..extensions import db

class Friendship(db.Model):
    __tablename__ = "friendships"

    id = db.Column(db.Integer, primary_key=True)

    requester_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    addressee_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status = db.Column(db.String(20), nullable=False, default="pending")

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("requester_id <> addressee_id", name="ck_friend_self"),
    )

    @staticmethod
    def between(u1_id: int, u2_id: int):
        return Friendship.query.filter(
            or_(
                db.and_(Friendship.requester_id == u1_id, Friendship.addressee_id == u2_id),
                db.and_(Friendship.requester_id == u2_id, Friendship.addressee_id == u1_id),
            )
        ).first()
