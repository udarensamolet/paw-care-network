from __future__ import annotations

import os
import sqlite3
from datetime import datetime

from flask import Flask, render_template
from flask_login import login_required, current_user

from sqlalchemy import event, or_
from sqlalchemy.engine import Engine

from .extensions import db, migrate, login_manager, csrf


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object("config.Config")

    os.makedirs(os.path.join(app.static_folder, "uploads"), exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite:"):
        opts = dict(app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {}))
        ca = dict(opts.get("connect_args", {}))
        ca.setdefault("check_same_thread", False)
        ca.setdefault("timeout", 30)
        opts["connect_args"] = ca
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = opts

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
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

    from .analytics.routes import analytics_bp
    app.register_blueprint(analytics_bp)

    from .cli import (
        init_db_cmd,
        reset_db_cmd,
        purge_data_cmd,
        seed_demo_cmd,
        seed_small_cmd,
        seed_big_cmd,
    )

    app.cli.add_command(init_db_cmd)
    app.cli.add_command(reset_db_cmd)
    app.cli.add_command(purge_data_cmd)
    app.cli.add_command(seed_demo_cmd)
    app.cli.add_command(seed_small_cmd)
    app.cli.add_command(seed_big_cmd)

    @app.get("/")
    def index():
        return render_template("home.html")

    @app.get("/dashboard")
    @login_required
    def dashboard():
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
            "sitter_assignments": CareAssignment.query.filter(
                CareAssignment.sitter_id == current_user.id,
                CareAssignment.status == "active",
                CareAssignment.end_at >= datetime.utcnow(),
            ).count(),
            "friends_open_reqs": (
                CareRequest.query.filter(
                    CareRequest.status == "open",
                    CareRequest.owner_id.in_(friend_ids),
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

    @app.context_processor
    def inject_helpers():
        def friendly_name(user):
            if not user:
                return ""
            name = (getattr(user, "name", None) or "").strip()
            if name:
                return name
            email = getattr(user, "email", "") or ""
            return email.split("@", 1)[0] if email else ""

        def fmt_date(dt):
            try:
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return ""

        def fmt_dt(dt):
            try:
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return ""

        def static_filename(path):
            if not path:
                return None
            p = str(path)
            if p.startswith("/static/"):
                return p[len("/static/") :]
            return p

        return dict(
            friendly_name=friendly_name,
            fmt_date=fmt_date,
            fmt_dt=fmt_dt,
            static_filename=static_filename,
            current_year=datetime.utcnow().year,
        )

    @app.teardown_request
    def _teardown_request(_exc):
        try:
            if _exc is not None:
                db.session.rollback()
        finally:
            db.session.remove()

    return app