from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Optional, Length
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, and_

from ..extensions import db
from ..models.care import CareRequest
from ..models.assignment import CareAssignment
from ..models.social import Friendship
from ..models.user import User

matching_bp = Blueprint("matching", __name__, template_folder="../templates")


class ApplyForm(FlaskForm):
    start_at = DateTimeLocalField(
        "I can start at", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    end_at = DateTimeLocalField(
        "I can stay until", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    sitter_note = TextAreaField(
        "Note to owner (optional)", validators=[Optional(), Length(max=1000)]
    )
    submit = SubmitField("Apply")


def _are_friends(user_id_a: int, user_id_b: int) -> bool:
    q = Friendship.query.filter(
        or_(
            and_(
                Friendship.requester_id == user_id_a,
                Friendship.addressee_id == user_id_b,
            ),
            and_(
                Friendship.requester_id == user_id_b,
                Friendship.addressee_id == user_id_a,
            ),
        ),
        Friendship.status == "accepted",
    )
    return db.session.query(q.exists()).scalar()


def _valid_interval(start_at, end_at) -> bool:
    try:
        return start_at and end_at and end_at > start_at
    except Exception:
        return False

@matching_bp.get("/requests/friends/open")
@login_required
def open_friend_requests():
    """List open care requests posted by my accepted friends."""
    rels = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(
            Friendship.requester_id == current_user.id,
            Friendship.addressee_id == current_user.id,
        ),
    ).all()
    friend_ids = [
        (r.addressee_id if r.requester_id == current_user.id else r.requester_id)
        for r in rels
    ]

    rows = []
    if friend_ids:
        rows = (
            CareRequest.query.options(joinedload(CareRequest.pet))
            .filter(CareRequest.status == "open", CareRequest.owner_id.in_(friend_ids))
            .order_by(CareRequest.start_at.asc())
            .all()
        )

    users = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
    users_map = {u.id: u for u in users}
    return render_template("open_friend_requests.html", rows=rows, users_map=users_map)


@matching_bp.route("/requests/<int:req_id>/apply", methods=["GET", "POST"])
@login_required
def apply_request(req_id):
    cr = CareRequest.query.options(joinedload(CareRequest.pet)).get_or_404(req_id)

    if cr.owner_id == current_user.id:
        abort(403)  # Owner can't apply to their own request

    if cr.status != "open":
        flash("This request is not open anymore.", "warning")
        return redirect(url_for("matching.open_friend_requests"))

    if not current_user.is_sitter:
        flash("You must have the Sitter role to apply.", "warning")
        return redirect(url_for("matching.open_friend_requests"))

    if not _are_friends(current_user.id, cr.owner_id):
        flash("You can apply only to requests from accepted friends.", "warning")
        return redirect(url_for("matching.open_friend_requests"))

    form = ApplyForm()

    if request.method == "GET":
        form.start_at.data = cr.start_at
        form.end_at.data = cr.end_at

    if form.validate_on_submit():
        start = form.start_at.data
        end = form.end_at.data

        if not _valid_interval(start, end):
            flash("End time must be after start time.", "warning")
            return render_template("apply_request.html", form=form, req=cr)

        if not (cr.start_at <= start and end <= cr.end_at):
            flash(
                "Your availability must fit within the owner's requested window.",
                "warning",
            )
            return render_template("apply_request.html", form=form, req=cr)

        a = CareAssignment(
            care_request_id=cr.id,
            sitter_id=current_user.id,
            pet_id=cr.pet_id,
            start_at=start,
            end_at=end,
            sitter_note=(form.sitter_note.data or None),
            status="pending",
        )
        db.session.add(a)
        db.session.commit()
        flash("Applied. The owner will review your application.", "success")
        return redirect(url_for("assignments.list_assignments"))

    return render_template("apply_request.html", form=form, req=cr)
