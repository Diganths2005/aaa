from fastapi.testclient import TestClient
import uuid

from main import app

client = TestClient(app)


def test_tax_trace_endpoint_is_deterministic():
    email = f"trace-{uuid.uuid4()}@example.com"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "first_name": "Trace", "last_name": "User", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    profile = client.post(
        "/api/v1/tax-profiles",
        headers=headers,
        json={
            "pan_number": "ABCDE1234F",
            "date_of_birth": "1990-01-01",
            "residential_status": "resident",
            "employment_type": "salaried",
            "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
            "taxes_paid": [{"tax_type": "tds", "amount": 20000}],
        },
    )
    assert profile.status_code == 200
    response = client.get("/api/v1/chat/trace?metric=taxable_income", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["metric"] == "taxable_income"
    assert any(node["id"] == "taxable_income" for node in body["nodes"])


def test_chat_response_includes_structured_source_details():
    email = f"source-{uuid.uuid4()}@example.com"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "first_name": "Source", "last_name": "User", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    response = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "How does the rebate work under the new regime?"},
    )
    assert response.status_code == 200
    assert response.json()["source_details"]
    assert response.json()["source_details"][0]["assessment_year"] == "2026-27"
