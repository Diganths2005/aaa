import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql://taxwise_user:taxwise_password@localhost:5432/taxwise_db")
os.environ.setdefault("SECRET_KEY", "ci-postgres-secret")
os.environ.setdefault("DOCUMENT_STORAGE_DIR", ".taxwise-data/postgres-smoke")

from sqlalchemy import text

from database import Base, SessionLocal, engine
from models.tax_profile import TaxProfile
from models.user import User
from utils.common import generate_id

Base.metadata.create_all(bind=engine)

with engine.connect() as connection:
    assert connection.execute(text("SELECT 1")).scalar() == 1
    assert connection.execute(text("SELECT to_regclass('public.revoked_tokens')")).scalar() == "revoked_tokens"

email = f"postgres-smoke-{uuid.uuid4()}@example.com"
user_id = generate_id()
profile_id = generate_id()
with SessionLocal() as db:
    db.add(User(id=user_id, email=email, first_name="Postgres", last_name="Smoke", hashed_password="test"))
    db.commit()
    db.add(TaxProfile(
        id=profile_id,
        user_id=user_id,
        pan_number=f"ABCD{uuid.uuid4().int % 10000:04d}F",
        date_of_birth="1990-01-15",
        residential_status="resident",
        employment_type="salaried",
        salary_income=[{"employer_name": "CI Employer", "gross_salary": "500000"}],
    ))
    db.commit()

with SessionLocal() as db:
    user = db.query(User).filter(User.id == user_id).one()
    profile = db.query(TaxProfile).filter(TaxProfile.id == profile_id, TaxProfile.user_id == user.id).one()
    assert profile.salary_income[0]["gross_salary"] == "500000"
    db.delete(profile)
    db.delete(user)
    db.commit()

print("PostgreSQL persistence smoke test passed")
