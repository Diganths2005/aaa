import os
import uuid

import pytest

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
    selection = client.get("/api/itr/selection", headers=headers)
    assert selection.json()["recommended_itr"] == "ITR-1"
    assert selection.json()["preparation_supported"] is True
    preparation = client.post("/api/itr/prepare", headers=headers, json={"regime": "new"})
    assert preparation.status_code == 200
    assert preparation.json()["calculation"]["total_tax"] is not None
    assert preparation.json()["calculation"]["tax_after_rebate"] is not None
    assert preparation.json()["calculation"]["slab_calculation"]
    assert preparation.json()["bank_accounts"][0]["account_number"] == "******3456"

    answer = client.post("/api/itr/ask", headers=headers, json={"question": "How much TDS have I already paid?"})
    assert "25,000" in answer.json()["assistant_message"]
    pdf = client.post("/api/itr/pdf", headers=headers, json={"regime": "new"})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


@pytest.mark.parametrize(
    ("itr_form", "profile_fields"),
    [
        (
            "ITR-2",
            {
                "salary_income": [{"employer_name": "Example Technologies", "gross_salary": 1000000}],
                "capital_gains": [{
                    "asset_type": "listed_equity_share",
                    "acquisition_date": "2024-01-01",
                    "sale_date": "2025-08-01",
                    "sale_consideration": 200000,
                    "acquisition_cost": 150000,
                    "quantity": 10,
                    "is_listed": True,
                    "stt_paid_on_acquisition": True,
                    "stt_paid_on_transfer": True,
                }],
            },
        ),
    ],
)
def test_itr2_selection_does_not_prepare_unsupported_return(itr_form, profile_fields):
    email = f"{itr_form.lower()}-{uuid.uuid4()}@example.com"
    signup = client.post("/api/v1/auth/signup", json={"email": email, "first_name": "Demo", "last_name": "Taxpayer", "password": "password123"})
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    profile = client.post("/api/v1/tax-profiles", headers=headers, json={
        "pan_number": unique_pan(),
        "date_of_birth": "1990-01-15",
        "residential_status": "resident",
        **profile_fields,
    })
    assert profile.status_code == 200

    selection = client.get("/api/itr/selection", headers=headers)
    assert selection.json()["recommended_itr"] == itr_form
    assert selection.json()["preparation_supported"] is False
    preparation = client.post("/api/itr/prepare", headers=headers, json={"regime": "new", "itr_form": itr_form})
    assert preparation.status_code == 422
    assert "outside the supported preparation scope" in preparation.json()["detail"]
    assert "No preparation summary was generated" in preparation.json()["detail"]

    pdf = client.post("/api/itr/pdf", headers=headers, json={"regime": "new", "itr_form": itr_form})
    assert pdf.status_code == 422


def test_itr3_api_prepares_business_income_review_summary_and_pdf():
    email = f"itr3-{uuid.uuid4()}@example.com"
    signup = client.post("/api/v1/auth/signup", json={"email": email, "first_name": "Demo", "last_name": "Business", "password": "password123"})
    headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    profile = client.post("/api/v1/tax-profiles", headers=headers, json={
        "date_of_birth": "1990-01-15",
        "residential_status": "resident",
        "employment_type": "self_employed",
        "has_business_income": True,
        "business_income": [{
            "business_name": "Consulting",
            "nature_of_business": "Professional services",
            "gross_receipts": 1000000,
            "net_profit_or_loss": 400000,
        }],
        "taxes_paid": [{"tax_type": "advance_tax", "amount": 25000}],
    })
    assert profile.status_code == 200

    selection = client.get("/api/itr/selection", headers=headers)
    assert selection.json()["recommended_itr"] == "ITR-3"
    assert selection.json()["preparation_supported"] is True

    preparation = client.post("/api/itr/prepare", headers=headers, json={"regime": "new", "itr_form": "ITR-3"})
    assert preparation.status_code == 200
    body = preparation.json()
    assert body["itr_form"] == "ITR-3"
    assert float(body["income"]["business"]) == 400000
    assert body["schedules"]["business_income"][0]["business_name"] == "Consulting"
    assert body["support_status"]["statutory_itr3_schedules"].startswith("Not supported")

    recalculated = client.post("/api/itr/recalculate", headers=headers, json={"regime": "old", "itr_form": "ITR-3"})
    assert recalculated.status_code == 200
    assert recalculated.json()["calculation"]["regime"] == "old"

    pdf = client.post("/api/itr/pdf", headers=headers, json={"regime": "new", "itr_form": "ITR-3"})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert b"Consulting" in pdf.content