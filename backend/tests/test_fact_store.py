import os
import uuid

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.document import UserDocument
from models.taxpayer_fact import TaxpayerFact, TaxpayerFactEvidence
from schemas.tax_profile import TaxProfileCreate
from services.document_projection import apply_fact_projection
from services.fact_store import persist_extracted_candidates, record_profile_facts
from services.profile_service import ProfileService
from utils.common import generate_id

client = TestClient(app)


def create_user():
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"facts-{uuid.uuid4()}@example.com",
            "first_name": "Fact",
            "last_name": "Tester",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    return {
        "id": response.json()["user"]["id"],
        "headers": {"Authorization": f"Bearer {response.json()['access_token']}"},
    }


def create_document(db, user_id, assessment_year="2026-27"):
    document = UserDocument(
        id=generate_id(),
        user_id=user_id,
        document_type="form_16",
        original_filename=f"fact-{uuid.uuid4()}.pdf",
        assessment_year=assessment_year,
        status="REQUIRES_CONFIRMATION",
    )
    db.add(document)
    db.flush()
    return document


def test_extraction_retains_unmapped_values_and_confirms_agreeing_sources():
    user = create_user()
    db = SessionLocal()
    try:
        first_document = create_document(db, user["id"])
        first_facts = persist_extracted_candidates(
            db,
            user_id=user["id"],
            assessment_year="2026-27",
            document_id=first_document.id,
            candidates=[
                {"field": "salary_income", "value": 840000, "source": "FORM16", "confidence": "high"},
                {"field": "future_extractor_field", "value": {"detail": "preserved"}, "source": "FORM16", "confidence": "high"},
            ],
            extracted_text="Gross salary 840000",
        )
        second_document = create_document(db, user["id"])
        second_facts = persist_extracted_candidates(
            db,
            user_id=user["id"],
            assessment_year="2026-27",
            document_id=second_document.id,
            candidates=[
                {"field": "salary_income", "value": 840000, "source": "AIS", "confidence": "high"},
            ],
            extracted_text="Salary income 840000",
        )
        db.commit()
        assert first_facts[0].status == "CONFIRMED"
        assert second_facts[0].status == "CONFIRMED"
        unknown = next(fact for fact in first_facts if fact.mapping_status == "UNMAPPED")
        assert unknown.fact_key == "raw.future_extractor_field"
        assert unknown.value == {"detail": "preserved"}
        assert db.query(TaxpayerFactEvidence).filter(TaxpayerFactEvidence.fact_id == unknown.id).count() == 1
        apply_fact_projection(db, user["id"], second_facts[0].fact_key, second_facts[0].value, second_facts[0].group_id)
        projected = ProfileService(db).get(user["id"])
        assert TaxProfileCreate.model_validate(projected).salary_income[0].gross_salary == 840000
    finally:
        db.close()


def test_conflict_resolution_protects_confirmed_values_and_projects_corrections():
    owner = create_user()
    other_user = create_user()
    db = SessionLocal()
    try:
        profile_data = TaxProfileCreate(
            pan_number="ABCDE1234F",
            salary_income=[{"employer_name": "Example Employer", "gross_salary": 800000}],
        )
        ProfileService(db).save(owner["id"], profile_data)
        record_profile_facts(db, owner["id"], profile_data)
        document = create_document(db, owner["id"])
        extracted = persist_extracted_candidates(
            db,
            user_id=owner["id"],
            assessment_year="2026-27",
            document_id=document.id,
            candidates=[
                {"field": "salary_income", "value": 900000, "source": "FORM16", "confidence": "high"},
            ],
            extracted_text="Gross salary 900000",
        )[0]
        db.commit()
        assert extracted.status == "CONFLICT"
        extracted_id = extracted.id
    finally:
        db.close()

    hidden = client.post(
        f"/api/v1/facts/{extracted_id}/resolve",
        headers=other_user["headers"],
        json={"action": "accept"},
    )
    assert hidden.status_code == 404

    kept = client.post(
        f"/api/v1/facts/{extracted_id}/resolve",
        headers=owner["headers"],
        json={"action": "keep"},
    )
    assert kept.status_code == 200
    profile_response = client.get("/api/v1/tax-profiles/current", headers=owner["headers"])
    assert profile_response.status_code == 200
    assert profile_response.json()["salary_income"][0]["gross_salary"] in {"800000", "800000.0"}

    db = SessionLocal()
    try:
        new_document = create_document(db, owner["id"])
        replacement = persist_extracted_candidates(
            db,
            user_id=owner["id"],
            assessment_year="2026-27",
            document_id=new_document.id,
            candidates=[
                {"field": "salary_income", "value": 1000000, "source": "FORM16", "confidence": "high"},
            ],
            extracted_text="Gross salary 1000000",
        )[0]
        db.commit()
        replacement_id = replacement.id
    finally:
        db.close()

    accepted = client.post(
        f"/api/v1/facts/{replacement_id}/resolve",
        headers=owner["headers"],
        json={"action": "accept"},
    )
    assert accepted.status_code == 200
    corrected = client.post(
        f"/api/v1/facts/{replacement_id}/resolve",
        headers=owner["headers"],
        json={"action": "correct", "value": 1100000},
    )
    assert corrected.status_code == 200
    profile_response = client.get("/api/v1/tax-profiles/current", headers=owner["headers"])
    assert profile_response.json()["salary_income"][0]["gross_salary"] in {"1100000", "1100000.0"}

    unowned_listing = client.get("/api/v1/facts/", headers=other_user["headers"])
    assert unowned_listing.status_code == 200
    assert all(item["id"] != extracted_id for item in unowned_listing.json())


def test_readiness_marks_income_requirement_from_confirmed_profile_facts():
    user = create_user()
    before = client.get("/api/v1/facts/readiness", headers=user["headers"])
    assert before.status_code == 200
    income = next(item for item in before.json()["requirements"] if item["key"] == "income_source")
    assert income["status"] == "MISSING"

    db = SessionLocal()
    try:
        profile = TaxProfileCreate(
            pan_number="ABCDE1234F",
            salary_income=[{"employer_name": "Example Employer", "gross_salary": 840000}],
        )
        ProfileService(db).save(user["id"], profile)
        record_profile_facts(db, user["id"], profile)
        db.commit()
    finally:
        db.close()

    after = client.get("/api/v1/facts/readiness", headers=user["headers"])
    income = next(item for item in after.json()["requirements"] if item["key"] == "income_source")
    assert income["status"] == "CONFIRMED"
    assert after.json()["ready"] is False
