from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from flask_wtf import FlaskForm
from wtforms.fields import EmailField
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint("auth", __name__, template_folder="../templates")

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    is_owner = BooleanField("Owner")
    is_sitter = BooleanField("Sitter")
    submit = SubmitField("Create account")

class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        # Проверка за уникален имейл
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email is already registered.", "warning")
            return redirect(url_for("auth.register"))

        user = User(
            email=form.email.data.lower(),
            name=form.name.data.strip(),
            is_owner=bool(form.is_owner.data),
            is_sitter=bool(form.is_sitter.data),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created and logged in.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", form=form)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if not user or not user.check_password(form.password.data):
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login"))
        login_user(user)
        flash("Signed in successfully.", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html", form=form)

@auth_bp.get("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash("Signed out.", "info")
    return redirect(url_for("auth.login"))