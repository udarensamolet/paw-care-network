import os
import sys
from datetime import datetime, timedelta

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.social import Friendship
from app.models.pet import Pet
from app.models.care import CareRequest
from app.models.assignment import CareAssignment


def _assert_memory_db(uri: str):
    if uri != "sqlite:///:memory:":
        raise RuntimeError(
            f"Refusing to run tests on non-memory DB: {uri!r}. "
            "This guard protects your real database."
        )


@pytest.fixture(scope="function")
def app():
    os.environ["FLASK_ENV"] = "testing"
    os.environ.pop("DATABASE_URL", None)

    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"check_same_thread": False}},
        SERVER_NAME="localhost",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    _assert_memory_db(flask_app.config["SQLALCHEMY_DATABASE_URI"])

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        _assert_memory_db(flask_app.config["SQLALCHEMY_DATABASE_URI"])
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def make_user(app):
    def _make_user(email: str, name: str, is_owner=False, is_sitter=False):
        u = User(email=email, name=name, is_owner=is_owner, is_sitter=is_sitter)
        if hasattr(u, "set_password"):
            u.set_password("pass")
        db.session.add(u)
        db.session.commit()
        return u
    return _make_user

@pytest.fixture()
def login_as(client, app):
    def _login_as(user: User):
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True
    return _login_as


@pytest.fixture()
def sample_data(app, make_user):
    owner = make_user("owner@example.com", "Owner", is_owner=True, is_sitter=False)
    sitter = make_user("sitter@example.com", "Sitter", is_owner=False, is_sitter=True)
    stranger = make_user("stranger@example.com", "Stranger", is_owner=False, is_sitter=True)

    f = Friendship(requester_id=owner.id, addressee_id=sitter.id, status="accepted")
    db.session.add(f)

    pet = Pet(owner_id=owner.id, name="Roshlyo", species="Cat", breed="Street Queen", age=7)
    db.session.add(pet)
    db.session.commit()

    now = datetime.utcnow()
    cr = CareRequest(
        owner_id=owner.id,
        pet_id=pet.id,
        start_at=now + timedelta(days=1, hours=1),
        end_at=now + timedelta(days=2, hours=1),
        status="open",
    )
    db.session.add(cr)
    db.session.commit()

    return {
        "owner": owner,
        "sitter": sitter,
        "stranger": stranger,
        "pet": pet,
        "request": cr,
    }

@pytest.fixture()
def future_interval():
    now = datetime.utcnow()
    return (
        (now + timedelta(days=1, hours=2)).strftime("%Y-%m-%dT%H:%M"),
        (now + timedelta(days=1, hours=20)).strftime("%Y-%m-%dT%H:%M"),
    )