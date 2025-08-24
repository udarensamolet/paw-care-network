from datetime import datetime

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload
from wtforms import SubmitField, TextAreaField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Length, Optional

from ..extensions import db
from ..models.assignment import CareAssignment
from ..models.care import CareRequest
from ..models.social import Friendship
from ..models.user import User

matching_bp = Blueprint("matching", __name__, template_folder="../templates")


class ApplyForm(FlaskForm):
    start_at = DateTimeLocalField("I can start at", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    end_at = DateTimeLocalField("I can stay until", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    sitter_note = TextAreaField("Note to owner (optional)", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Apply")


def _are_friends(user_id_a: int, user_id_b: int) -> bool:
    q = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == user_id_a, Friendship.addressee_id == user_id_b),
            and_(Friendship.requester_id == user_id_b, Friendship.addressee_id == user_id_a),
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
    """List open care requests posted by my accepted friends (with simple pagination)."""
    # Friends
    rels = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == current_user.id, Friendship.addressee_id == current_user.id),
    ).all()
    friend_ids = [(r.addressee_id if r.requester_id == current_user.id else r.requester_id) for r in rels]

    rows, has_next, has_prev, page = [], False, False, 1
    if friend_ids:
        page = request.args.get("page", 1, type=int)
        per_page = 10
        base = (
            CareRequest.query.options(joinedload(CareRequest.pet))
            .filter(CareRequest.status == "open", CareRequest.owner_id.in_(friend_ids))
            .order_by(CareRequest.start_at.asc())
        )
        fetched = base.offset((page - 1) * per_page).limit(per_page + 1).all()
        has_next = len(fetched) > per_page
        has_prev = page > 1
        rows = fetched[:per_page]

    users = User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []
    users_map = {u.id: u for u in users}
    return render_template(
        "open_friend_requests.html",
        rows=rows,
        users_map=users_map,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
    )


@matching_bp.route("/requests/<int:req_id>/apply", methods=["GET", "POST"])
@login_required
def apply_request(req_id):
    cr = CareRequest.query.options(joinedload(CareRequest.pet)).get_or_404(req_id)

    if cr.owner_id == current_user.id:
        abort(403)

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

    now = datetime.utcnow()
    min_start = cr.start_at if cr.start_at > now else now
    max_end = cr.end_at

    if request.method == "GET":
        form.start_at.data = cr.start_at
        form.end_at.data = cr.end_at

    if form.validate_on_submit():
        start = form.start_at.data
        end = form.end_at.data

        if not _valid_interval(start, end):
            flash("End time must be after start time.", "warning")
            return render_template("apply_request.html", form=form, req=cr, min_start=min_start, max_end=max_end)

        if start < now:
            flash("Start time cannot be in the past.", "warning")
            return render_template("apply_request.html", form=form, req=cr, min_start=min_start, max_end=max_end)

        if not (cr.start_at <= start and end <= cr.end_at):
            flash("Your availability must fit within the owner's requested window.", "warning")
            return render_template("apply_request.html", form=form, req=cr, min_start=min_start, max_end=max_end)

        existing = CareAssignment.query.filter_by(
            care_request_id=cr.id, sitter_id=current_user.id
        ).first()
        if existing:
            flash("You have already applied for this request.", "info")
            return redirect(url_for("assignments.list_assignments"))

        overlap = CareAssignment.query.filter(
            CareAssignment.sitter_id == current_user.id,
            CareAssignment.status.in_(["pending", "active"]),
            CareAssignment.start_at < end,
            CareAssignment.end_at > start,
        ).first()
        if overlap:
            flash("You already have another assignment overlapping these times.", "warning")
            return render_template("apply_request.html", form=form, req=cr, min_start=min_start, max_end=max_end)

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

    return render_template("apply_request.html", form=form, req=cr, min_start=min_start, max_end=max_end)