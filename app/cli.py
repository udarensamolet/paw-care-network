from __future__ import annotations

import random
from datetime import datetime, timedelta

import click
from flask import current_app
from sqlalchemy import text

from .extensions import db

from .models.user import User
from .models.pet import Pet
from .models.care import CareRequest
from .models.assignment import CareAssignment
from .models.social import Friendship


def _db_uri() -> str:
    return current_app.config.get("SQLALCHEMY_DATABASE_URI", "")

@click.command("init-db")
def init_db_cmd():
    uri = _db_uri()
    click.echo(f"Creating tables on DB: {uri}")
    db.create_all()
    click.echo("✔ Tables created.")

@click.command("reset-db")
@click.option("--force", is_flag=True, help="Drop + create (НЕОБРАТИМО).")
def reset_db_cmd(force: bool):
    uri = _db_uri()
    if not force:
        click.echo("Add --force to confirm dropping all tables.")
        return
    click.echo(f"Dropping & creating tables on DB: {uri}")
    db.drop_all()
    db.create_all()
    click.echo("✔ Database reset.")

@click.command("purge-data")
def purge_data_cmd():
    db.session.query(CareAssignment).delete()
    db.session.query(CareRequest).delete()
    db.session.query(Pet).delete()
    db.session.query(Friendship).delete()
    db.session.query(User).delete()
    db.session.commit()
    try:
        db.session.execute(text("DELETE FROM sqlite_sequence"))
        db.session.commit()
    except Exception:
        pass
    click.echo("✔ All data removed (schema kept).")

@click.command("seed-demo")
def seed_demo_cmd():
    owner = User(email="demo@paw.com", name="Demo Owner", is_owner=True, is_sitter=False)
    if hasattr(owner, "set_password"):
        owner.set_password("demo")
    db.session.add(owner)
    db.session.commit()

    sitter = User(email="sitter@paw.com", name="Demo Sitter", is_owner=False, is_sitter=True)
    if hasattr(sitter, "set_password"):
        sitter.set_password("demo")
    db.session.add(sitter)
    db.session.commit()

    f = Friendship(requester_id=owner.id, addressee_id=sitter.id, status="accepted")
    db.session.add(f)

    pet = Pet(owner_id=owner.id, name="Maca", species="Cat", breed="Mix", age=3)
    db.session.add(pet)
    db.session.commit()

    now = datetime.utcnow()
    cr = CareRequest(
        owner_id=owner.id,
        pet_id=pet.id,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=2),
        status="open",
    )
    db.session.add(cr)
    db.session.commit()

    click.echo("✔ Seed done. Users: demo@paw.com / sitter@paw.com (парола: demo)")

FIRST_NAMES = [
    "Alex", "Mira", "Daniel", "Eva", "Ivo", "Nina", "Chris", "Maria", "Petar", "Georgi",
    "Viktor", "Sofia", "Ani", "Stoyan", "Kalina", "Toma", "Raya", "Mila", "Rumen", "Teo",
]
LAST_NAMES = [
    "Petrov", "Georgieva", "Ivanov", "Dimitrova", "Nikolov", "Stoyanova", "Kolev",
    "Marinova", "Kostov", "Hristova", "Vasilev", "Todorova", "Alexandrov", "Ilieva",
]

SPECIES_BREEDS = {
    "Cat": ["Domestic Shorthair", "British Shorthair", "Siamese", "Maine Coon", "Mix"],
    "Dog": ["Labrador", "German Shepherd", "Golden Retriever", "Bulldog", "Poodle", "Mix"],
    "Bird": ["Budgerigar", "Cockatiel", "Canary", "Lovebird", "Parrot"],
    "Hamster": ["Syrian", "Dwarf Campbell", "Winter White", "Chinese", "Roborovski"],
    "Rabbit": ["Holland Lop", "Mini Lop", "Netherland Dwarf", "Lionhead", "Mix"],
}

def _rand_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _rand_email(i: int) -> str:
    return f"user{i:03d}@paw.com"

def _rand_pet(owner_id: int) -> Pet:
    species = random.choice(list(SPECIES_BREEDS.keys()))
    breed = random.choice(SPECIES_BREEDS[species])
    age = random.randint(1, 14)
    name = random.choice(
        ["Maca", "Rex", "Bobi", "Luna", "Simba", "Molly", "Kaya", "Pufi", "Rocky", "Tara", "Miro", "Sisi"]
    )
    p = Pet(owner_id=owner_id, name=name, species=species, breed=breed, age=age)
    db.session.add(p)
    return p

def _ensure_friendship(a_id: int, b_id: int, status: str = "accepted") -> None:
    if a_id == b_id:
        return
    exists = Friendship.query.filter(
        db.or_(
            db.and_(Friendship.requester_id == a_id, Friendship.addressee_id == b_id),
            db.and_(Friendship.requester_id == b_id, Friendship.addressee_id == a_id),
        )
    ).first()
    if exists:
        return
    f = Friendship(requester_id=a_id, addressee_id=b_id, status=status)
    db.session.add(f)

def _make_assignment_for_request(
    req: CareRequest, sitter_id: int, mode: str, now: datetime
) -> CareAssignment:
    if mode == "assigned":
        start = req.start_at
        end = req.end_at
        status = "pending"
    elif mode == "active":
        start = now - timedelta(hours=random.randint(1, 6))
        end = now + timedelta(hours=random.randint(2, 12))
        req.start_at = start
        req.end_at = end
        status = "active"
    else:
        duration_h = random.randint(2, 24)
        end = now - timedelta(days=random.randint(1, 20), hours=random.randint(0, 12))
        start = end - timedelta(hours=duration_h)
        status = "done"

    a = CareAssignment(
        care_request_id=req.id,
        sitter_id=sitter_id,
        start_at=start,
        end_at=end,
        status=status,
        sitter_note=random.choice(
            ["Happy to help!", "Evening walks OK.", "Can do meds.", "Near the owner.", "Flexible hours."]
        ),
    )
    db.session.add(a)
    return a

def _seed_bulk(
    users: int,
    pets_per_owner_min: int,
    pets_per_owner_max: int,
    reqs_per_pet_min: int,
    reqs_per_pet_max: int,
) -> None:
    random.seed(42)
    uri = _db_uri()
    click.echo(f"Seeding on DB: {uri}")

    now = datetime.utcnow()

    all_users: list[User] = []
    for i in range(users):
        role_pick = random.random()
        is_owner = role_pick < 0.4 or (0.7 <= role_pick <= 1.0) 
        is_sitter = role_pick > 0.3                             
        u = User(email=_rand_email(i), name=_rand_name(), is_owner=is_owner, is_sitter=is_sitter)
        if hasattr(u, "set_password"):
            u.set_password("demo")
        db.session.add(u)
        all_users.append(u)
    db.session.commit()

    owners = [u for u in all_users if u.is_owner]
    sitters = [u for u in all_users if u.is_sitter]
    click.echo(f"Users: total={len(all_users)} owners={len(owners)} sitters={len(sitters)}")

    for o in owners:
        candidates = random.sample(sitters, k=min(4, len(sitters))) if sitters else []
        for s in candidates[:3]:
            _ensure_friendship(o.id, s.id, status="accepted")
        if len(candidates) >= 4:
            _ensure_friendship(o.id, candidates[3].id, status="pending")
    db.session.commit()

    pets: list[Pet] = []
    for o in owners:
        k = random.randint(pets_per_owner_min, pets_per_owner_max)
        for _ in range(k):
            p = _rand_pet(o.id)
            pets.append(p)
    db.session.commit()
    click.echo(f"Pets: total={len(pets)}")

    total_reqs = 0
    total_asg = 0
    status_weights = [
        ("open", 0.30),
        ("assigned", 0.20),
        ("active", 0.20),
        ("done", 0.25),
        ("cancelled", 0.05),
    ]

    def pick_status() -> str:
        r = random.random()
        acc = 0.0
        for label, w in status_weights:
            acc += w
            if r <= acc:
                return label
        return "open"

    for p in pets:
        rels = Friendship.query.filter(
            db.and_(
                Friendship.status == "accepted",
                db.or_(
                    Friendship.requester_id == p.owner_id,
                    Friendship.addressee_id == p.owner_id,
                ),
            )
        ).all()
        friend_ids = [
            (r.addressee_id if r.requester_id == p.owner_id else r.requester_id) for r in rels
        ]
        friend_sitters = [u for u in all_users if u.id in friend_ids and u.is_sitter]

        k = random.randint(reqs_per_pet_min, reqs_per_pet_max)
        for _ in range(k):
            days_offset = random.randint(-40, 40)
            start = now + timedelta(days=days_offset, hours=random.randint(7, 19))
            end = start + timedelta(hours=random.randint(2, 36))
            st = pick_status()

            req = CareRequest(
                owner_id=p.owner_id,
                pet_id=p.id,
                start_at=start,
                end_at=end,
                status=st,
            )
            db.session.add(req)
            db.session.flush()  

            if friend_sitters and st in {"assigned", "active", "done"}:
                sitter = random.choice(friend_sitters)
                _make_assignment_for_request(req, sitter.id, mode=st, now=now)
                total_asg += 1

            total_reqs += 1

    db.session.commit()
    click.echo(f"CareRequests: total={total_reqs}")
    click.echo(f"Assignments: total={total_asg}")

    open_reqs = CareRequest.query.filter_by(status="open").count()
    active_asg = CareAssignment.query.filter_by(status="active").count()
    done_asg = CareAssignment.query.filter_by(status="done").count()
    pending_asg = CareAssignment.query.filter_by(status="pending").count()

    click.echo(
        "✔ Seed completed:\n"
        f"  Users: {len(all_users)}\n"
        f"  Pets: {len(pets)}\n"
        f"  Requests: {total_reqs} (open: {open_reqs})\n"
        f"  Assignments: {total_asg} (pending: {pending_asg}, active: {active_asg}, done: {done_asg})"
    )

@click.command("seed-small")
@click.option("--users", default=20, show_default=True, help="Общ брой потребители.")
@click.option("--pets-per-owner-min", default=1, show_default=True, help="Мин. брой pets на owner.")
@click.option("--pets-per-owner-max", default=2, show_default=True, help="Макс. брой pets на owner.")
@click.option("--reqs-per-pet-min", default=1, show_default=True, help="Мин. заявки за pet.")
@click.option("--reqs-per-pet-max", default=3, show_default=True, help="Макс. заявки за pet.")
def seed_small_cmd(
    users: int,
    pets_per_owner_min: int,
    pets_per_owner_max: int,
    reqs_per_pet_min: int,
    reqs_per_pet_max: int,
):
    _seed_bulk(users, pets_per_owner_min, pets_per_owner_max, reqs_per_pet_min, reqs_per_pet_max)

@click.command("seed-big")
@click.option("--users", default=40, show_default=True, help="Общ брой потребители.")
@click.option("--pets-per-owner-min", default=1, show_default=True, help="Мин. брой pets на owner.")
@click.option("--pets-per-owner-max", default=3, show_default=True, help="Макс. брой pets на owner.")
@click.option("--reqs-per-pet-min", default=2, show_default=True, help="Мин. заявки за pet.")
@click.option("--reqs-per-pet-max", default=5, show_default=True, help="Макс. заявки за pet.")
def seed_big_cmd(
    users: int,
    pets_per_owner_min: int,
    pets_per_owner_max: int,
    reqs_per_pet_min: int,
    reqs_per_pet_max: int,
):
    _seed_bulk(users, pets_per_owner_min, pets_per_owner_max, reqs_per_pet_min, reqs_per_pet_max)