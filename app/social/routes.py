from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from ..extensions import db
from ..models.user import User
from ..models.social import Friendship

social_bp = Blueprint("social", __name__, template_folder="../templates")

@social_bp.route("/search", methods=["GET"])
@login_required
def search():
    q_raw = (request.args.get("q") or "").strip()
    results, status_map = [], {}

    if q_raw:
        q_lower = q_raw.lower()
        base = User.query.filter(User.id != current_user.id)

        if "@" in q_raw:
            results = (base
                       .filter(func.lower(User.email).contains(q_lower))
                       .order_by(User.id.asc())
                       .limit(50).all())
        else:
            tokens = [t for t in q_lower.split() if t]
            q = base
            for t in tokens:
                q = q.filter(func.lower(User.name).contains(t))
            results = q.order_by(User.id.asc()).limit(50).all()

        if results:
            ids = [u.id for u in results]
            rels = (Friendship.query
                    .filter(or_(Friendship.requester_id == current_user.id,
                                Friendship.addressee_id == current_user.id))
                    .filter(or_(Friendship.requester_id.in_(ids),
                                Friendship.addressee_id.in_(ids)))
                    .all())

            status_map = {uid: "none" for uid in ids}
            for f in rels:
                other = f.addressee_id if f.requester_id == current_user.id else f.requester_id
                if f.status == "accepted":
                    status_map[other] = "friends"
                elif f.status == "pending":
                    status_map[other] = "sent" if f.requester_id == current_user.id else "incoming"

    return render_template("social_search.html", q=q_raw, results=results, status_map=status_map)

def _redirect_back_to_search():
    q = request.args.get("q") or request.form.get("q")
    if q:
        return redirect(url_for("social.search", q=q))
    return redirect(url_for("social.sent"))

@social_bp.post("/send/<int:user_id>")
@login_required
def send_request(user_id):
    if user_id == current_user.id:
        return _redirect_back_to_search()

    other = User.query.get_or_404(user_id)

    existing = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == user_id),
            and_(Friendship.requester_id == user_id,           Friendship.addressee_id == current_user.id),
        )
    ).first()

    if existing:
        if existing.status == "accepted":
            return _redirect_back_to_search()
        if existing.status == "pending":
            if existing.requester_id == user_id:
                existing.status = "accepted"
                db.session.commit()
                return redirect(url_for("social.friends"))
            return _redirect_back_to_search()

    fr = Friendship(requester_id=current_user.id, addressee_id=user_id, status="pending")
    db.session.add(fr)
    db.session.commit()
    return redirect(url_for("social.sent"))

@social_bp.post("/cancel/<int:user_id>")
@login_required
def cancel(user_id):
    fr = Friendship.query.filter_by(requester_id=current_user.id, addressee_id=user_id, status="pending").first()
    if fr:
        db.session.delete(fr)
        db.session.commit()
    return redirect(url_for("social.sent"))

@social_bp.post("/accept/<int:user_id>")
@login_required
def accept(user_id):
    fr = Friendship.query.filter_by(requester_id=user_id, addressee_id=current_user.id, status="pending").first()
    if fr:
        fr.status = "accepted"
        db.session.commit()
    return redirect(url_for("social.friends"))

@social_bp.post("/decline/<int:user_id>")
@login_required
def decline(user_id):
    fr = Friendship.query.filter_by(requester_id=user_id, addressee_id=current_user.id, status="pending").first()
    if fr:
        db.session.delete(fr)
        db.session.commit()
    return redirect(url_for("social.incoming"))

@social_bp.get("/sent")
@login_required
def sent():
    rels = Friendship.query.filter_by(requester_id=current_user.id, status="pending").all()
    ids = [r.addressee_id for r in rels]
    users = User.query.filter(User.id.in_(ids)).all() if ids else []
    u_map = {u.id: u for u in users}
    rows = [{"user": u_map[r.addressee_id], "friendship": r} for r in rels if r.addressee_id in u_map]
    return render_template("social_sent.html", rows=rows)

@social_bp.get("/incoming")
@login_required
def incoming():
    rels = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()
    ids = [r.requester_id for r in rels]
    users = User.query.filter(User.id.in_(ids)).all() if ids else []
    u_map = {u.id: u for u in users}
    rows = [{"user": u_map[r.requester_id], "friendship": r} for r in rels if r.requester_id in u_map]
    return render_template("social_incoming.html", rows=rows)

@social_bp.get("/friends")
@login_required
def friends():
    rels = Friendship.query.filter(
        or_(Friendship.requester_id == current_user.id, Friendship.addressee_id == current_user.id),
        Friendship.status == "accepted"
    ).all()
    ids = [(r.addressee_id if r.requester_id == current_user.id else r.requester_id) for r in rels]
    users = User.query.filter(User.id.in_(ids)).all() if ids else []
    return render_template("social_friends.html", users=users)