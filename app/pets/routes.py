from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from werkzeug.utils import secure_filename
from wtforms import StringField, IntegerField, TextAreaField, SubmitField
from wtforms.fields import URLField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, URL
import os
import time as pytime

from ..extensions import db
from ..models.pet import Pet

pets_bp = Blueprint("pets", __name__, template_folder="../templates")


class PetForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    species = StringField("Species", validators=[Optional(), Length(max=50)])
    breed = StringField("Breed", validators=[Optional(), Length(max=120)])
    age = IntegerField(
        "Age (years)", validators=[Optional(), NumberRange(min=0, max=1000)]
    )
    care_instructions = TextAreaField("Care instructions", validators=[Optional()])
    notes = TextAreaField("Notes", validators=[Optional()])
    photo_url = URLField(
        "Photo URL", validators=[Optional(), URL(message="Enter a valid URL")]
    )
    photo_file = FileField("Upload photo", validators=[FileAllowed(["jpg","jpeg","png","gif"], "Images only!")])
    submit = SubmitField("Save")


def _require_owner():
    if not current_user.is_owner:
        flash("Only owners can manage pets.", "warning")
        return False
    return True


def _get_owned_pet_or_404(pet_id: int) -> Pet:
    return Pet.query.filter_by(id=pet_id, owner_id=current_user.id).first_or_404()


@pets_bp.route("/pets", methods=["GET"])
@login_required
def list_pets():
    if not _require_owner():
        return redirect(url_for("dashboard"))
    pets = (
        Pet.query.filter_by(owner_id=current_user.id)
        .order_by(Pet.created_at.desc())
        .all()
    )
    return render_template("pets_list.html", pets=pets)


@pets_bp.route("/pets/new", methods=["GET", "POST"])
@login_required
def create_pet():
    if not _require_owner():
        return redirect(url_for("dashboard"))
    form = PetForm()
    if form.validate_on_submit():
        pet = Pet(
            owner_id=current_user.id,
            name=form.name.data.strip(),
            species=(form.species.data or "").strip() or None,
            breed=(form.breed.data or "").strip() or None,
            age=form.age.data,
            care_instructions=form.care_instructions.data,
            notes=form.notes.data,
            photo_url=(form.photo_url.data or "").strip() or None,
        )
        if form.photo_file.data:
            filename = secure_filename(form.photo_file.data.filename)
            if filename:
                name, ext = os.path.splitext(filename)
                unique = f"{int(pytime.time())}_{current_user.id}{ext.lower()}"
                upload_dir = os.path.join(current_app.static_folder, "uploads")
                file_path = os.path.join(upload_dir, unique)
                form.photo_file.data.save(file_path)
                pet.photo_url = f"/static/uploads/{unique}"
        db.session.add(pet)
        db.session.commit()
        flash("Pet created.", "success")
        return redirect(url_for("pets.list_pets"))
    return render_template("pet_form.html", form=form, mode="create")


@pets_bp.route("/pets/<int:pet_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pet(pet_id):
    if not _require_owner():
        return redirect(url_for("dashboard"))
    pet = _get_owned_pet_or_404(pet_id)
    form = PetForm(obj=pet)
    if form.validate_on_submit():
        pet.name = form.name.data.strip()
        pet.species = (form.species.data or "").strip() or None
        pet.breed = (form.breed.data or "").strip() or None
        pet.age = form.age.data
        pet.care_instructions = form.care_instructions.data
        pet.notes = form.notes.data
        pet.photo_url = (form.photo_url.data or "").strip() or None
        if form.photo_file.data:
            filename = secure_filename(form.photo_file.data.filename)
            if filename:
                name, ext = os.path.splitext(filename)
                unique = f"{int(pytime.time())}_{current_user.id}{ext.lower()}"
                upload_dir = os.path.join(current_app.static_folder, "uploads")
                file_path = os.path.join(upload_dir, unique)
                form.photo_file.data.save(file_path)
                pet.photo_url = f"/static/uploads/{unique}"
        db.session.commit()
        flash("Pet updated.", "success")
        return redirect(url_for("pets.list_pets"))
    return render_template("pet_form.html", form=form, mode="edit", pet=pet)


@pets_bp.route("/pets/<int:pet_id>/delete", methods=["POST"])
@login_required
def delete_pet(pet_id):
    if not _require_owner():
        return redirect(url_for("dashboard"))
    pet = _get_owned_pet_or_404(pet_id)
    db.session.delete(pet)
    db.session.commit()
    flash("Pet deleted.", "info")
    return redirect(url_for("pets.list_pets"))
