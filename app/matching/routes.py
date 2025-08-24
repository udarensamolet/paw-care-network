from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Optional
from sqlalchemy import or_

from ..extensions import db
from ..models.care import CareRequest  # care_requests
from ..models.assignment import CareAssignment  # care_assignments
from ..models.social import Friendship

matching_bp = Blueprint("matching", __name__, template_folder="../templates")


# --- Forms ---
class ApplyForm(FlaskForm):
    start_at = DateTimeLocalField(
        "I can start at", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    end_at = DateTimeLocalField(
        "I can stay until", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    sitter_note = TextAreaField("Note to owner (optional)", validators=[Optional()])
    submit = SubmitField("Send to owner")


def _friend_ids_of(uid: int):
    rels = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == uid, Friendship.addressee_id == uid),
    ).all()
    return [r.addressee_id if r.requester_id == uid else r.requester_id for r in rels]


def _has_sitter_overlap(sitter_id: int, start_at, end_at) -> bool:
    q = CareAssignment.query.filter(
        CareAssignment.sitter_id == sitter_id,
        CareAssignment.status == "active",
        CareAssignment.start_at < end_at,
        CareAssignment.end_at > start_at,
    )
    return db.session.query(q.exists()).scalar()


def _has_pet_overlap(pet_id: int | None, start_at, end_at) -> bool:
    if not pet_id:
        return False
    q = CareAssignment.query.filter(
        CareAssignment.pet_id == pet_id,
        CareAssignment.status == "active",
        CareAssignment.start_at < end_at,
        CareAssignment.end_at > start_at,
    )
    return db.session.query(q.exists()).scalar()

@matching_bp.route("/requests/open-friends", methods=["GET"])
@login_required
def open_friend_requests():
    friend_ids = _friend_ids_of(current_user.id)
    rows = (
        (
            CareRequest.query.filter(
                CareRequest.status == "open", CareRequest.owner_id.in_(friend_ids)
            )
            .order_by(CareRequest.start_at.asc())
            .limit(50)
            .all()
        )
        if friend_ids
        else []
    )
    return render_template("friend_requests.html", rows=rows)

@matching_bp.route("/requests/<int:req_id>/apply", methods=["GET", "POST"])
@login_required
def apply_request(req_id):
    cr = CareRequest.query.get_or_404(req_id)

    if cr.owner_id == current_user.id:
        flash("You cannot apply to your own request.", "warning")
        return redirect(url_for("schedule.care_list"))

    if cr.owner_id not in _friend_ids_of(current_user.id):
        flash("You can apply only to friends' requests.", "danger")
        return redirect(url_for("matching.open_friend_requests"))

    if cr.status != "open":
        flash("This request is not open anymore.", "info")
        return redirect(url_for("matching.open_friend_requests"))

    form = ApplyForm()

    if request.method == "GET":
        form.start_at.data = cr.start_at
        form.end_at.data = cr.end_at

    if form.validate_on_submit():
        start_at = form.start_at.data
        end_at = form.end_at.data

        if end_at <= start_at:
            flash("End must be after start.", "warning")
            return render_template("apply_request.html", form=form, req=cr)
        
        if not (cr.start_at <= start_at and end_at <= cr.end_at):
            flash("Your proposed time must be within the request window.", "warning")
            return render_template("apply_request.html", form=form, req=cr)

        if _has_sitter_overlap(current_user.id, start_at, end_at):
            flash("You have a conflicting active assignment.", "warning")
            return render_template("apply_request.html", form=form, req=cr)
        if _has_pet_overlap(cr.pet_id, start_at, end_at):
            flash(
                "This pet already has an active assignment in that window.", "warning"
            )
            return render_template("apply_request.html", form=form, req=cr)

        existing = CareAssignment.query.filter_by(
            care_request_id=cr.id, sitter_id=current_user.id, status="pending"
        ).first()
        if existing:
            flash("You already have a pending application for this request.", "info")
            return redirect(url_for("assignments.review_list"))

        a = CareAssignment(
            care_request_id=cr.id,
            sitter_id=current_user.id,
            pet_id=cr.pet_id,
            start_at=start_at,
            end_at=end_at,
            sitter_note=(form.sitter_note.data or "").strip() or None,
            status="pending",
        )
        db.session.add(a)
        db.session.commit()

        flash("Application sent to the owner. Await approval.", "success")
        return redirect(url_for("assignments.list_assignments"))

    return render_template("apply_request.html", form=form, req=cr)
