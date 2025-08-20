from flask import Flask
from .extensions import db, migrate, login_manager

def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    @app.get("/")
    def index():
        return "Paw Care Network — API is alive."

    return app