from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models.assignment import CareAssignment
from ..models.care import CareRequest

assignments_bp = Blueprint("assignments", __name__, template_folder="../templates")

@assignments_bp.route("/assignments", methods=["GET"])
@login_required
def list_assignments():
    owner_rows = (
        db.session.query(CareAssignment)
        .join(CareRequest, CareRequest.id == CareAssignment.care_request_id)
        .options(joinedload(CareAssignment.__table__))
        .filter(CareRequest.owner_id == current_user.id)
        .order_by(CareAssignment.start_at.desc())
        .all()
    )

    sitter_rows = (
        CareAssignment.query.filter_by(sitter_id=current_user.id)
        .order_by(CareAssignment.start_at.desc())
        .all()
    )

    return render_template(
        "assignments_list.html", owner_rows=owner_rows, sitter_rows=sitter_rows
    )

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