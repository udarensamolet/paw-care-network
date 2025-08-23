from flask import Flask, render_template_string, redirect, url_for
from flask_login import login_required, current_user
from .extensions import db, migrate, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    from .models.user import User

    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return "Paw Care Network — API is alive. Go to /auth/register or /auth/login."

    @app.get("/dashboard")
    @login_required
    def dashboard():
        # Минимален защитен екран без шаблон, за MVP
        return render_template_string(
            "<h1>Welcome, {{ user.name }}!</h1>"
            "<p>Email: {{ user.email }}</p>"
            '<p><a href="{{ url_for("auth.logout") }}">Logout</a></p>',
            user=current_user,
        )

    return app