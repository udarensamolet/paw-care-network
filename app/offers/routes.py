from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import Optional, Length
from sqlalchemy import and_

from ..extensions import db
from ..models.care import CareRequest
from ..models.offer import CareOffer
from ..models.assignment import CareAssignment
from ..models.social import Friendship

offers_bp = Blueprint("offers", __name__, template_folder="../templates")


class OfferForm(FlaskForm):
    message = TextAreaField(
        "Message (optional)", validators=[Optional(), Length(max=2000)]
    )
    submit = SubmitField("Send offer")


class AcceptForm(FlaskForm):
    submit = SubmitField("Accept")


class DeclineForm(FlaskForm):
    submit = SubmitField("Decline")


class WithdrawForm(FlaskForm):
    submit = SubmitField("Withdraw")


def _are_friends(u1_id: int, u2_id: int) -> bool:
    f = Friendship.between(u1_id, u2_id)
    return bool(f and f.status == "accepted")


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


@offers_bp.route("/offers/mine", methods=["GET"])
@login_required
def my_offers():
    rows = (
        CareOffer.query.filter_by(sitter_id=current_user.id)
        .order_by(CareOffer.created_at.desc())
        .all()
    )
    withdraw_forms = {
        r.id: WithdrawForm(prefix=f"w{r.id}") for r in rows if r.status == "offered"
    }
    return render_template("offers_mine.html", rows=rows, withdraw_forms=withdraw_forms)


@offers_bp.route("/offers/request/<int:req_id>/new", methods=["GET", "POST"])
@login_required
def offer_new(req_id):
    cr = CareRequest.query.get_or_404(req_id)
    if cr.owner_id == current_user.id:
        flash("You can't offer on your own request.", "warning")
        return redirect(url_for("schedule.care_list"))

    if not _are_friends(current_user.id, cr.owner_id):
        flash("You can offer only on friends' requests.", "warning")
        return redirect(url_for("schedule.care_list"))

    form = OfferForm()
    if form.validate_on_submit():
        if not current_user.is_sitter:
            current_user.is_sitter = True

        existing = CareOffer.query.filter_by(
            care_request_id=cr.id, sitter_id=current_user.id, status="offered"
        ).first()
        if existing:
            flash("You already have an active offer for this request.", "info")
            return redirect(url_for("offers.my_offers"))

        offer = CareOffer(
            care_request_id=cr.id,
            sitter_id=current_user.id,
            message=(form.message.data or "").strip() or None,
            status="offered",
        )
        db.session.add(offer)
        db.session.commit()
        flash("Offer sent.", "success")
        return redirect(url_for("offers.my_offers"))

    return render_template("offer_form.html", form=form, req=cr)


@offers_bp.route("/offers/<int:offer_id>/withdraw", methods=["POST"])
@login_required
def offer_withdraw(offer_id):
    form = WithdrawForm(prefix=f"w{offer_id}")
    if not form.validate_on_submit():
        flash("Invalid action.", "warning")
        return redirect(url_for("offers.my_offers"))
    off = CareOffer.query.get_or_404(offer_id)
    if off.sitter_id != current_user.id or off.status != "offered":
        flash("Not allowed.", "danger")
        return redirect(url_for("offers.my_offers"))
    off.status = "withdrawn"
    db.session.commit()
    flash("Offer withdrawn.", "info")
    return redirect(url_for("offers.my_offers"))


@offers_bp.route("/offers/request/<int:req_id>", methods=["GET"])
@login_required
def offers_for_request(req_id):
    cr = CareRequest.query.get_or_404(req_id)
    if cr.owner_id != current_user.id:
        flash("Only the owner can view offers for this request.", "danger")
        return redirect(url_for("schedule.care_list"))
    rows = (
        CareOffer.query.filter_by(care_request_id=cr.id)
        .order_by(CareOffer.created_at.desc())
        .all()
    )
    accept_forms = {
        r.id: AcceptForm(prefix=f"a{r.id}") for r in rows if r.status == "offered"
    }
    decline_forms = {
        r.id: DeclineForm(prefix=f"d{r.id}") for r in rows if r.status == "offered"
    }
    return render_template(
        "offers_for_request.html",
        req=cr,
        rows=rows,
        accept_forms=accept_forms,
        decline_forms=decline_forms,
    )


@offers_bp.route("/offers/<int:offer_id>/accept", methods=["POST"])
@login_required
def offer_accept(offer_id):
    form = AcceptForm(prefix=f"a{offer_id}")
    if not form.validate_on_submit():
        flash("Invalid action.", "warning")
        return redirect(url_for("schedule.care_list"))

    off = CareOffer.query.get_or_404(offer_id)
    cr = CareRequest.query.get_or_404(off.care_request_id)
    if cr.owner_id != current_user.id or off.status != "offered":
        flash("Not allowed.", "danger")
        return redirect(url_for("schedule.care_list"))

    if _has_sitter_overlap(off.sitter_id, cr.start_at, cr.end_at):
        flash("This sitter has a conflicting assignment.", "warning")
        return redirect(url_for("offers.offers_for_request", req_id=cr.id))
    if _has_pet_overlap(cr.pet_id, cr.start_at, cr.end_at):
        flash("This pet already has a conflicting assignment.", "warning")
        return redirect(url_for("offers.offers_for_request", req_id=cr.id))

    assign = CareAssignment(
        care_request_id=cr.id,
        sitter_id=off.sitter_id,
        pet_id=cr.pet_id,
        start_at=cr.start_at,
        end_at=cr.end_at,
        status="active",
    )
    db.session.add(assign)

    off.status = "accepted_by_owner"
    cr.status = "confirmed"
    db.session.commit()

    flash("Offer accepted. Assignment created.", "success")
    return redirect(url_for("assignments.list_assignments"))


@offers_bp.route("/offers/<int:offer_id>/decline", methods=["POST"])
@login_required
def offer_decline(offer_id):
    form = DeclineForm(prefix=f"d{offer_id}")
    if not form.validate_on_submit():
        flash("Invalid action.", "warning")
        return redirect(url_for("schedule.care_list"))

    off = CareOffer.query.get_or_404(offer_id)
    cr = CareRequest.query.get_or_404(off.care_request_id)
    if cr.owner_id != current_user.id or off.status != "offered":
        flash("Not allowed.", "danger")
        return redirect(url_for("schedule.care_list"))

    off.status = "declined_by_owner"
    db.session.commit()
    flash("Offer declined.", "info")
    return redirect(url_for("offers.offers_for_request", req_id=cr.id))