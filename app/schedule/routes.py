from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.fields import DateTimeLocalField
from wtforms.validators import DataRequired, Optional, Length

from ..extensions import db
from ..models.pet import Pet
from ..models.care import CareRequest

schedule_bp = Blueprint("schedule", __name__, template_folder="../templates")


class CareRequestForm(FlaskForm):
    pet_id = SelectField("Pet", coerce=int, validators=[Optional()])
    start_at = DateTimeLocalField(
        "Start", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    end_at = DateTimeLocalField(
        "End", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )
    location_text = StringField(
        "Location (optional)", validators=[Optional(), Length(max=255)]
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")


def _require_owner():
    if not current_user.is_owner:
        flash("Only owners can create/view care requests.", "warning")
        return False
    return True


def _owner_request_or_404(req_id: int) -> CareRequest:
    return CareRequest.query.filter_by(
        id=req_id, owner_id=current_user.id
    ).first_or_404()


@schedule_bp.route("/care/requests", methods=["GET"])
@login_required
def care_list():
    if not _require_owner():
        return redirect(url_for("dashboard"))
    reqs = (
        CareRequest.query.filter_by(owner_id=current_user.id)
        .order_by(CareRequest.start_at.desc())
        .all()
    )
    return render_template("care_list.html", requests=reqs)


@schedule_bp.route("/care/requests/new", methods=["GET", "POST"])
@login_required
def care_create():
    if not _require_owner():
        return redirect(url_for("dashboard"))
    form = CareRequestForm()

    pets = Pet.query.filter_by(owner_id=current_user.id).order_by(Pet.name).all()
    form.pet_id.choices = [(0, "-- No pet --")] + [(p.id, p.name) for p in pets]

    if form.validate_on_submit():
        pet_id = form.pet_id.data or 0
        pet_id = None if pet_id == 0 else pet_id

        start_at = form.start_at.data
        end_at = form.end_at.data
        if end_at <= start_at:
            flash("End must be after Start.", "warning")
            return render_template("care_form.html", form=form, mode="create")

        cr = CareRequest(
            owner_id=current_user.id,
            pet_id=pet_id,
            start_at=start_at,
            end_at=end_at,
            location_text=(form.location_text.data or "").strip() or None,
            notes=form.notes.data,
        )
        db.session.add(cr)
        db.session.commit()
        flash("Care request created.", "success")
        return redirect(url_for("schedule.care_list"))
    return render_template("care_form.html", form=form, mode="create")


@schedule_bp.route("/care/requests/<int:req_id>/edit", methods=["GET", "POST"])
@login_required
def care_edit(req_id):
    if not _require_owner():
        return redirect(url_for("dashboard"))
    cr = _owner_request_or_404(req_id)
    if cr.status in ("cancelled", "completed"):
        flash("Cannot edit a cancelled or completed request.", "warning")
        return redirect(url_for("schedule.care_list"))

    form = CareRequestForm(obj=cr)

    pets = Pet.query.filter_by(owner_id=current_user.id).order_by(Pet.name).all()
    form.pet_id.choices = [(0, "-- No pet --")] + [(p.id, p.name) for p in pets]
    form.pet_id.data = cr.pet_id or 0

    if form.validate_on_submit():
        cr.pet_id = None if (form.pet_id.data or 0) == 0 else form.pet_id.data
        cr.start_at = form.start_at.data
        cr.end_at = form.end_at.data
        if cr.end_at <= cr.start_at:
            flash("End must be after Start.", "warning")
            return render_template("care_form.html", form=form, mode="edit", req=cr)
        cr.location_text = (form.location_text.data or "").strip() or None
        cr.notes = form.notes.data
        db.session.commit()
        flash("Care request updated.", "success")
        return redirect(url_for("schedule.care_list"))
    return render_template("care_form.html", form=form, mode="edit", req=cr)


@schedule_bp.route("/care/requests/<int:req_id>/cancel", methods=["POST"])
@login_required
def care_cancel(req_id):
    if not _require_owner():
        return redirect(url_for("dashboard"))
    cr = _owner_request_or_404(req_id)
    cr.status = "cancelled"
    db.session.commit()
    flash("Care request cancelled.", "info")
    return redirect(url_for("schedule.care_list"))