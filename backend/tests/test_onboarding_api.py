import os
import uuid
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)

USED_PANS = set()


def unique_pan():
    while True:
        pan = f"ABCDE{uuid.uuid4().int % 10000:04d}F"
        if pan not in USED_PANS:
            USED_PANS.add(pan)
            return pan


def authenticated_client():
    email = f"onboarding-{uuid.uuid4()}@example.com"
    response = client.post("/api/v1/auth/signup", json={"email": email, "first_name": "Test", "last_name": "User", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_session_message_and_confirmation_updates_profile():
    headers = authenticated_client()
    session = client.post("/api/v1/onboarding/session", headers=headers)
    assert session.status_code == 200
    assert session.json()["current_field"] == "name"

    # Move through required personal questions to reach salary.
    for answer in ("Test User", "ABCDE1234F", "1990-01-01", "resident", "salaried", "Acme"):
        answer = unique_pan() if answer == "ABCDE1234F" else answer
        response = client.post("/api/v1/onboarding/message", headers=headers, json={"message": answer})
        assert response.status_code == 200
        if response.json()["requires_confirmation"]:
            confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
            assert confirmed.status_code == 200

    response = client.post("/api/v1/onboarding/message", headers=headers, json={"message": "6.5 lakh"})
    assert response.status_code == 200
    assert response.json()["candidate_values"]["salary_income"][0]["gross_salary"] == 650000
    assert response.json()["requires_confirmation"] is True

    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    assert Decimal(confirmed.json()["profile"]["salary_income"][0]["gross_salary"]) == Decimal("650000")


def test_onboarding_reject_does_not_create_profile_from_candidate():
    headers = authenticated_client()
    client.post("/api/v1/onboarding/session", headers=headers)
    for answer in ("Test User", unique_pan(), "1990-01-01", "resident", "salaried", "Acme", "6 lakh"):
        response = client.post("/api/v1/onboarding/message", headers=headers, json={"message": answer})
        if response.json().get("requires_confirmation"):
            if answer == "6 lakh":
                break
            client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    rejected = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "reject"})
    assert rejected.status_code == 200
    assert rejected.json()["profile"]["salary_income"] == []


def test_document_candidate_with_tds_but_no_salary_does_not_crash():
    headers = authenticated_client()
    candidate = client.post(
        "/api/v1/onboarding/document-candidate",
        headers=headers,
        json={"candidate_values": {"salary_tds": "150000", "deductions": [{"section": "80D", "amount": "25000"}]}},
    )
    assert candidate.status_code == 200

    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    profile = confirmed.json()["profile"]
    assert profile["salary_income"] == []
    assert {item["tax_type"] for item in profile["taxes_paid"]} == {"tds"}


def test_document_candidate_does_not_duplicate_tds_tax_payment():
    headers = authenticated_client()
    candidate = client.post(
        "/api/v1/onboarding/document-candidate",
        headers=headers,
        json={
            "candidate_values": {
                "salary_tds": "150000",
                "taxes_paid": [
                    {"tax_type": "tds", "amount": "150000"},
                    {"tax_type": "advance_tax", "amount": "50000"},
                ],
            }
        },
    )
    assert candidate.status_code == 200

    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    assert confirmed.json()["profile"]["taxes_paid"] == [
        {"tax_type": "tds", "amount": "150000", "reference": None},
        {"tax_type": "advance_tax", "amount": "50000", "reference": None},
    ]