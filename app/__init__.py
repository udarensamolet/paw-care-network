from flask import Flask, redirect, url_for, render_template
from flask_login import login_required, current_user
from .extensions import db, migrate, login_manager
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    os.makedirs(os.path.join(app.static_folder, "uploads"), exist_ok=True)

    from .models.user import User
    from .models.social import Friendship
    from .models.pet import Pet

    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from .social.routes import social_bp
    app.register_blueprint(social_bp, url_prefix="/social")

    from .pets.routes import pets_bp
    app.register_blueprint(pets_bp)

    from .models.care import CareRequest

    from .schedule.routes import schedule_bp
    app.register_blueprint(schedule_bp)

    from .models.offer import CareOffer 
    from .models.assignment import CareAssignment  

    from .offers.routes import offers_bp
    app.register_blueprint(offers_bp, url_prefix="")

    from .assignments.routes import assignments_bp
    app.register_blueprint(assignments_bp, url_prefix="")   

    @app.get("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return render_template("home.html")

    @app.get("/dashboard")
    @login_required
    def dashboard():
        from .models.pet import Pet
        from .models.care import CareRequest
        from .models.offer import CareOffer
        from .models.assignment import CareAssignment

        stats = {
            "pets": Pet.query.filter_by(owner_id=current_user.id).count(),
            "open_requests": CareRequest.query.filter_by(owner_id=current_user.id, status="open").count(),
            "my_offers": CareOffer.query.filter_by(sitter_id=current_user.id).count(),
            "owner_assignments": (
                CareAssignment.query.join(CareRequest, CareRequest.id == CareAssignment.care_request_id)
                .filter(CareRequest.owner_id == current_user.id).count()
            ),
            "sitter_assignments": CareAssignment.query.filter_by(sitter_id=current_user.id).count(),
        }

        latest = {
            "requests": CareRequest.query.filter_by(owner_id=current_user.id)
                            .order_by(CareRequest.created_at.desc()).limit(5).all(),
            "offers": CareOffer.query.filter_by(sitter_id=current_user.id)
                        .order_by(CareOffer.created_at.desc()).limit(5).all(),
        }

        return render_template("dashboard.html", user=current_user, stats=stats, latest=latest)
    
    return app