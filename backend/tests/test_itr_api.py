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


def test_itr_api_end_to_end():
    email = f"itr-{uuid.uuid4()}@example.com"
    pan = unique_pan()
    signup = client.post("/api/v1/auth/signup", json={"email": email, "first_name": "Demo", "last_name": "Taxpayer", "password": "password123"})
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    profile = client.post("/api/v1/tax-profiles", headers=headers, json={
        "pan_number": pan, "date_of_birth": "2005-01-15", "residential_status": "resident",
        "employment_type": "salaried", "salary_income": [{"employer_name": "Example Technologies", "gross_salary": 600000, "standard_deduction": 0, "professional_tax": 0, "tds": 25000}],
        "taxes_paid": [{"tax_type": "tds", "amount": 25000}],
        "bank_accounts": [{"bank_name": "Demo Bank", "account_number": "000000123456", "ifsc_code": "DEMO0000001", "account_type": "savings", "is_primary": True}],
    })
    assert profile.status_code == 200

    eligibility = client.post("/api/itr/eligibility", headers=headers)
    assert eligibility.json()["eligible"] is True
    preparation = client.post("/api/itr/prepare", headers=headers, json={"regime": "new"})
    assert preparation.status_code == 200
    assert preparation.json()["calculation"]["total_tax"] is not None
    assert preparation.json()["bank_accounts"][0]["account_number"] == "******3456"

    answer = client.post("/api/itr/ask", headers=headers, json={"question": "How much TDS have I already paid?"})
    assert "25,000" in answer.json()["assistant_message"]
    pdf = client.post("/api/itr/pdf", headers=headers, json={"regime": "new"})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")