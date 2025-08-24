from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms.fields import DateTimeLocalField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.assignment import CareAssignment
from ..models.care import CareRequest

assignments_bp = Blueprint("assignments", __name__, template_folder="../templates")


class ApproveForm(FlaskForm):
    start_at = DateTimeLocalField(
        "Start", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    end_at = DateTimeLocalField(
        "End", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    submit = SubmitField("Approve")


class DeclineForm(FlaskForm):
    submit = SubmitField("Decline")


@assignments_bp.route("/assignments", methods=["GET"])
@login_required
def list_assignments():

    owner_rows = (
        db.session.query(CareAssignment)
        .options(joinedload(CareAssignment.pet), joinedload(CareAssignment.sitter))
        .join(CareRequest, CareRequest.id == CareAssignment.care_request_id)
        .filter(CareRequest.owner_id == current_user.id)
        .order_by(CareAssignment.start_at.desc())
        .all()
    )

    sitter_rows = (
        CareAssignment.query.options(
            joinedload(CareAssignment.pet), joinedload(CareAssignment.sitter)
        )
        .filter_by(sitter_id=current_user.id)
        .order_by(CareAssignment.start_at.desc())
        .all()
    )

    return render_template(
        "assignments_list.html", owner_rows=owner_rows, sitter_rows=sitter_rows
    )


@assignments_bp.route("/assignments/review", methods=["GET"])
@login_required
def review_list():
    rows = (
        db.session.query(CareAssignment)
        .options(joinedload(CareAssignment.pet), joinedload(CareAssignment.sitter))
        .join(CareRequest, CareRequest.id == CareAssignment.care_request_id)
        .filter(
            CareRequest.owner_id == current_user.id, CareAssignment.status == "pending"
        )
        .order_by(CareAssignment.created_at.desc())
        .all()
    )

    approve_forms = {}
    decline_forms = {}
    for a in rows:
        f = ApproveForm(prefix=f"ap{a.id}")
        f.start_at.data = a.start_at
        f.end_at.data = a.end_at
        approve_forms[a.id] = f
        decline_forms[a.id] = DeclineForm(prefix=f"dc{a.id}")
    return render_template(
        "assignments_owner_review.html",
        rows=rows,
        approve_forms=approve_forms,
        decline_forms=decline_forms,
    )


@assignments_bp.route("/assignments/<int:assign_id>/approve", methods=["POST"])
@login_required
def approve_assignment(assign_id):
    a = CareAssignment.query.get_or_404(assign_id)
    cr = CareRequest.query.get_or_404(a.care_request_id)
    if cr.owner_id != current_user.id or a.status != "pending":
        flash("Not allowed.", "danger")
        return redirect(url_for("assignments.review_list"))

    form = ApproveForm(prefix=f"ap{a.id}")
    if not form.validate_on_submit():
        flash("Invalid form.", "warning")
        return redirect(url_for("assignments.review_list"))

    new_start = form.start_at.data
    new_end = form.end_at.data
    if new_end <= new_start:
        flash("End must be after start.", "warning")
        return redirect(url_for("assignments.review_list"))

    if not (cr.start_at <= new_start and new_end <= cr.end_at):
        flash("Approved time must be within the request window.", "warning")
        return redirect(url_for("assignments.review_list"))

    conflict_sitter = CareAssignment.query.filter(
        CareAssignment.id != a.id,
        CareAssignment.sitter_id == a.sitter_id,
        CareAssignment.status == "active",
        CareAssignment.start_at < new_end,
        CareAssignment.end_at > new_start,
    ).first()

    conflict_pet = None
    if a.pet_id:
        conflict_pet = CareAssignment.query.filter(
            CareAssignment.id != a.id,
            CareAssignment.pet_id == a.pet_id,
            CareAssignment.status == "active",
            CareAssignment.start_at < new_end,
            CareAssignment.end_at > new_start,
        ).first()

    if conflict_sitter or conflict_pet:
        flash("Time conflicts with another active assignment.", "warning")
        return redirect(url_for("assignments.review_list"))

    a.start_at = new_start
    a.end_at = new_end
    a.status = "active"
    db.session.commit()

    if a.start_at == cr.start_at and a.end_at == cr.end_at:
        cr.status = "confirmed"
        db.session.commit()

    flash("Assignment approved.", "success")
    return redirect(url_for("assignments.list_assignments"))


@assignments_bp.route("/assignments/<int:assign_id>/decline", methods=["POST"])
@login_required
def decline_assignment(assign_id):
    a = CareAssignment.query.get_or_404(assign_id)
    cr = CareRequest.query.get_or_404(a.care_request_id)
    if cr.owner_id != current_user.id or a.status != "pending":
        flash("Not allowed.", "danger")
        return redirect(url_for("assignments.review_list"))

    form = DeclineForm(prefix=f"dc{a.id}")
    if not form.validate_on_submit():
        flash("Invalid form.", "warning")
        return redirect(url_for("assignments.review_list"))

    a.status = "declined"
    db.session.commit()
    flash("Application declined.", "info")
    return redirect(url_for("assignments.review_list"))


@assignments_bp.route("/assignments/<int:assign_id>/cancel", methods=["POST"])
@login_required
def cancel_assignment(assign_id):
    a = CareAssignment.query.get_or_404(assign_id)
    cr = CareRequest.query.get_or_404(a.care_request_id)
    if cr.owner_id != current_user.id:
        flash("Only the owner can cancel this assignment.", "danger")
        return redirect(url_for("assignments.list_assignments"))
    if a.status != "active":
        flash("Assignment is not active.", "info")
        return redirect(url_for("assignments.list_assignments"))

    a.status = "cancelled"
    db.session.commit()
    flash("Assignment cancelled.", "info")
    return redirect(url_for("assignments.list_assignments"))
