import os
import uuid
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas

from main import app

client = TestClient(app)


def signup(prefix: str):
    response = client.post("/api/v1/auth/signup", json={
        "email": f"{prefix}-{uuid.uuid4()}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "password123",
    })
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, response.json()["access_token"]


def unique_pan() -> str:
    return f"ABCDE{uuid.uuid4().int % 10000:04d}F"


def test_logout_revokes_the_current_jwt():
    headers, _ = signup("logout")
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_cross_user_profile_document_and_itr_isolation():
    owner, _ = signup("owner")
    other, _ = signup("other")

    created = client.post("/api/v1/tax-profiles", headers=owner, json={
        "pan_number": unique_pan(),
        "date_of_birth": "1990-01-15",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Owner Employer", "gross_salary": 900000}],
    })
    assert created.status_code == 200
    profile_id = created.json()["id"]

    assert client.get(f"/api/v1/tax-profiles/{profile_id}", headers=other).status_code == 404
    assert client.put(f"/api/v1/tax-profiles/{profile_id}", headers=other, json={"address": "attacker"}).status_code == 404
    assert client.delete(f"/api/v1/tax-profiles/{profile_id}", headers=other).status_code == 404
    assert client.get("/api/itr/selection", headers=other).status_code == 404

    pdf = BytesIO()
    canvas = Canvas(pdf)
    canvas.drawString(40, 780, "Gross Salary: Rs. 900000")
    canvas.save()
    upload = client.post("/api/v1/documents/upload", headers=owner, files={"file": ("private.pdf", pdf.getvalue(), "application/pdf")})
    assert upload.status_code == 202
    document_id = upload.json()["id"]

    assert client.get(f"/api/v1/documents/{document_id}/content", headers=other).status_code == 404
    assert client.post(f"/api/v1/documents/{document_id}/process", headers=other).status_code == 404
    assert client.delete(f"/api/v1/documents/{document_id}", headers=other).status_code == 404


def test_protected_api_rejects_missing_or_malformed_auth():
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/tax-profiles/current"),
        ("GET", "/api/v1/documents/"),
        ("GET", "/api/itr/selection"),
    ]
    for method, path in endpoints:
        response = client.request(method, path)
        assert response.status_code == 401
    malformed = client.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"})
    assert malformed.status_code == 401


def test_profile_and_tax_api_validation_rejects_invalid_payloads():
    headers, _ = signup("validation")
    invalid_profile = client.post("/api/v1/tax-profiles", headers=headers, json={
        "pan_number": "INVALID",
        "date_of_birth": "1990-01-15",
        "salary_income": [{"employer_name": "Employer", "gross_salary": -1}],
    })
    assert invalid_profile.status_code == 422

    invalid_tax = client.post("/api/tax/calculate", json={
        "profile": {"salary_income": [{"employer_name": "", "gross_salary": 100000}]},
        "regime": "new",
    })
    assert invalid_tax.status_code == 422


def test_end_to_end_user_flow_upload_confirm_calculate_and_prepare():
    headers, _ = signup("e2e")
    pan = unique_pan()
    pdf = BytesIO()
    canvas = Canvas(pdf)
    for index, line in enumerate([
        "Employee Name: E2E Taxpayer",
        f"PAN: {pan}",
        "Date of Birth: 15/01/1990",
        "Employer: E2E Employer",
        "Gross Salary: Rs. 840000",
        "TDS Deducted: Rs. 42000",
    ]):
        canvas.drawString(40, 780 - index * 24, line)
    canvas.save()

    upload = client.post("/api/v1/documents/upload", headers=headers, files={"file": ("e2e.pdf", pdf.getvalue(), "application/pdf")})
    assert upload.status_code == 202
    document_id = upload.json()["id"]
    processed = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert processed.status_code == 200
    candidate = client.post("/api/v1/onboarding/document-candidate", headers=headers, json={
        "candidate_values": processed.json()["onboarding_values"],
        "document_id": document_id,
    })
    assert candidate.status_code == 200
    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200

    profile = client.get("/api/v1/tax-profiles/current", headers=headers)
    assert profile.status_code == 200
    calc = client.post("/api/tax/calculate", json={"profile": profile.json(), "regime": "new"})
    assert calc.status_code == 200
    selection = client.get("/api/itr/selection", headers=headers)
    assert selection.status_code == 200
    preparation = client.post("/api/itr/prepare", headers=headers, json={"regime": "new"})
    assert preparation.status_code == 200
    assert preparation.json()["itr_form"] == "ITR-1"


def test_signup_rejects_weak_credentials_and_invalid_email():
    weak = client.post("/api/v1/auth/signup", json={
        "email": "bad-email",
        "first_name": "Test",
        "last_name": "User",
        "password": "short",
    })
    assert weak.status_code == 422
    invalid_email = client.post("/api/v1/auth/signup", json={
        "email": "not-an-email",
        "first_name": "Test",
        "last_name": "User",
        "password": "password123",
    })
    assert invalid_email.status_code == 422
