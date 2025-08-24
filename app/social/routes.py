from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import Length
from sqlalchemy import or_

from ..extensions import db
from ..models.user import User
from ..models.social import Friendship

social_bp = Blueprint("social", __name__, template_folder="../templates")


class SendRequestForm(FlaskForm):
    submit = SubmitField("Add friend")


class AcceptForm(FlaskForm):
    submit = SubmitField("Accept")


class DeclineForm(FlaskForm):
    submit = SubmitField("Decline")


class SearchForm(FlaskForm):
    q = StringField("Search by name or email", validators=[Length(min=0, max=255)])
    submit = SubmitField("Search")


def _friend_of(user_id: int):
    """Връща списък User на приятелите на user_id (accepted)."""
    rels = Friendship.query.filter(
        Friendship.status == "accepted",
        or_(Friendship.requester_id == user_id, Friendship.addressee_id == user_id),
    ).all()
    ids = [
        r.addressee_id if r.requester_id == user_id else r.requester_id for r in rels
    ]
    if not ids:
        return []
    return User.query.filter(User.id.in_(ids)).all()


@social_bp.route("/friends", methods=["GET"])
@login_required
def friends():
    friends = _friend_of(current_user.id)
    return render_template("social_friends.html", friends=friends)


@social_bp.route("/incoming", methods=["GET"])
@login_required
def incoming():
    reqs = Friendship.query.filter_by(
        addressee_id=current_user.id, status="pending"
    ).all()
    accept_forms = {r.id: AcceptForm(prefix=f"a{r.id}") for r in reqs}
    decline_forms = {r.id: DeclineForm(prefix=f"d{r.id}") for r in reqs}
    return render_template(
        "social_incoming.html",
        requests=reqs,
        accept_forms=accept_forms,
        decline_forms=decline_forms,
    )


@social_bp.route("/incoming/<int:fid>/accept", methods=["POST"])
@login_required
def incoming_accept(fid):
    form = AcceptForm(prefix=f"a{fid}")
    if not form.validate_on_submit():
        flash("Invalid request.", "warning")
        return redirect(url_for("social.incoming"))

    fr = Friendship.query.get_or_404(fid)
    if fr.addressee_id != current_user.id or fr.status != "pending":
        flash("Not allowed.", "danger")
        return redirect(url_for("social.incoming"))

    fr.status = "accepted"
    db.session.commit()
    flash("Friend request accepted.", "success")
    return redirect(url_for("social.friends"))


@social_bp.route("/incoming/<int:fid>/decline", methods=["POST"])
@login_required
def incoming_decline(fid):
    form = DeclineForm(prefix=f"d{fid}")
    if not form.validate_on_submit():
        flash("Invalid request.", "warning")
        return redirect(url_for("social.incoming"))

    fr = Friendship.query.get_or_404(fid)
    if fr.addressee_id != current_user.id or fr.status != "pending":
        flash("Not allowed.", "danger")
        return redirect(url_for("social.incoming"))

    db.session.delete(fr)
    db.session.commit()
    flash("Friend request declined.", "info")
    return redirect(url_for("social.incoming"))


@social_bp.route("/sent", methods=["GET"])
@login_required
def sent():
    reqs = Friendship.query.filter_by(
        requester_id=current_user.id, status="pending"
    ).all()
    return render_template("social_sent.html", requests=reqs)


@social_bp.route("/search", methods=["GET", "POST"])
@login_required
def search():
    form = SearchForm()
    send_forms = {}
    results = []

    if form.validate_on_submit():
        q = form.q.data.strip().lower()
        if q:
            results = (
                User.query.filter(
                    User.id != current_user.id,
                    or_(User.email.ilike(f"%{q}%"), User.name.ilike(f"%{q}%")),
                )
                .limit(20)
                .all()
            )
            send_forms = {u.id: SendRequestForm(prefix=f"s{u.id}") for u in results}
    return render_template(
        "social_search.html", form=form, results=results, send_forms=send_forms
    )


@social_bp.route("/request/<int:user_id>", methods=["POST"])
@login_required
def send_request(user_id):
    form = SendRequestForm(prefix=f"s{user_id}")
    if not form.validate_on_submit():
        flash("Invalid request.", "warning")
        return redirect(url_for("social.search"))

    if user_id == current_user.id:
        flash("You cannot add yourself.", "warning")
        return redirect(url_for("social.search"))

    target = User.query.get_or_404(user_id)

    existing = Friendship.between(current_user.id, target.id)
    if existing:
        if existing.status == "accepted":
            flash("You are already friends.", "info")
            return redirect(url_for("social.friends"))

        if (
            existing.status == "pending"
            and existing.requester_id == target.id
            and existing.addressee_id == current_user.id
        ):
            existing.status = "accepted"
            db.session.commit()
            flash("Friend request accepted.", "success")
            return redirect(url_for("social.friends"))
        flash("Friend request already sent.", "info")
        return redirect(url_for("social.sent"))

    fr = Friendship(
        requester_id=current_user.id, addressee_id=target.id, status="pending"
    )
    db.session.add(fr)
    db.session.commit()
    flash("Friend request sent.", "success")
    return redirect(url_for("social.sent"))