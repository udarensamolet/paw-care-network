from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db: SQLAlchemy = SQLAlchemy()
migrate: Migrate = Migrate()
login_manager = LoginManager()
csrf: CSRFProtect = CSRFProtect()