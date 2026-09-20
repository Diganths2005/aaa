import os
import uuid

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


def authenticated_headers():
    email = f"chat-{uuid.uuid4()}@example.com"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "first_name": "Chat", "last_name": "User", "password": "password123"},
    )
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


def test_chat_rejects_non_tax_question():
    headers = authenticated_headers()
    response = client.post("/api/v1/chat", headers=headers, json={"message": "Write Python code."})
    assert response.status_code == 200
    assert "personal tax assistant" in response.json()["answer"].lower()


def test_chat_uses_tax_profile_for_regime_question():
    headers = authenticated_headers()
    profile = client.post(
        "/api/v1/tax-profiles",
        headers=headers,
        json={
            "pan_number": unique_pan(),
            "date_of_birth": "1990-01-01",
            "residential_status": "resident",
            "employment_type": "salaried",
            "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
            "taxes_paid": [{"tax_type": "tds", "amount": 20000}],
        },
    )
    assert profile.status_code == 200

    response = client.post("/api/v1/chat", headers=headers, json={"message": "Which regime is better for me?"})
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert "regime" in answer or "tax" in answer
