from flask import Flask, render_template
from .extensions import db, migrate, login_manager
from flask_login import login_required, current_user


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    import os

    os.makedirs(os.path.join(app.static_folder, "uploads"), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"


    from .models.user import User  
    from .models.social import Friendship  
    from .models.pet import Pet  
    from .models.care import CareRequest  
    from .models.assignment import CareAssignment 

    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from .social.routes import social_bp
    app.register_blueprint(social_bp, url_prefix="/social")

    from .pets.routes import pets_bp
    app.register_blueprint(pets_bp)

    from .schedule.routes import schedule_bp
    app.register_blueprint(schedule_bp)

    from .matching.routes import matching_bp
    app.register_blueprint(matching_bp)

    from .assignments.routes import assignments_bp
    app.register_blueprint(assignments_bp)

    @app.get("/")
    def index():
        return render_template("home.html")

    @app.get("/dashboard")
    @login_required
    def dashboard():
        from .models.social import Friendship
        from .models.pet import Pet
        from .models.care import CareRequest
        from .models.assignment import CareAssignment
        from sqlalchemy import or_

        rels = Friendship.query.filter(
            Friendship.status == "accepted",
            or_(
                Friendship.requester_id == current_user.id,
                Friendship.addressee_id == current_user.id,
            ),
        ).all()
        friend_ids = [
            (r.addressee_id if r.requester_id == current_user.id else r.requester_id)
            for r in rels
        ]

        stats = {
            "pets": Pet.query.filter_by(owner_id=current_user.id).count(),
            "open_requests": CareRequest.query.filter_by(
                owner_id=current_user.id, status="open"
            ).count(),
            "sitter_assignments": CareAssignment.query.filter_by(
                sitter_id=current_user.id
            ).count(),
            "friends_open_reqs": (
                CareRequest.query.filter(
                    CareRequest.status == "open", CareRequest.owner_id.in_(friend_ids)
                ).count()
                if friend_ids
                else 0
            ),
            "pending_approvals": (
                CareAssignment.query.join(
                    CareRequest, CareRequest.id == CareAssignment.care_request_id
                )
                .filter(
                    CareRequest.owner_id == current_user.id,
                    CareAssignment.status == "pending",
                )
                .count()
            ),
        }

        latest = {
            "requests": CareRequest.query.filter_by(owner_id=current_user.id)
            .order_by(CareRequest.start_at.desc())
            .limit(5)
            .all(),
        }

        return render_template(
            "dashboard.html", user=current_user, stats=stats, latest=latest
        )

    return app