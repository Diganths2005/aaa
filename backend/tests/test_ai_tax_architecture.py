import os
import uuid
from copy import deepcopy

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from main import app
from routes import chat as chat_route
from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import compare_regimes

client = TestClient(app)

USED_PANS = set()


def unique_pan():
    while True:
        pan = f"ABCDE{uuid.uuid4().int % 10000:04d}F"
        if pan not in USED_PANS:
            USED_PANS.add(pan)
            return pan


def authenticated_headers():
    email = f"arch-{uuid.uuid4()}@example.com"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "first_name": "Arch", "last_name": "User", "password": "password123"},
    )
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


def test_tax_engine_produces_regime_numbers():
    profile = TaxProfileCreate(
        pan_number=unique_pan(),
        date_of_birth="1990-01-01",
        residential_status="resident",
        employment_type="salaried",
        salary_income=[
            {
                "employer_name": "Acme",
                "gross_salary": 1200000,
                "standard_deduction": 50000,
                "professional_tax": 0,
                "tds": 20000,
            }
        ],
        taxes_paid=[{"tax_type": "tds", "amount": 20000}],
    )

    comparison = compare_regimes(profile)

    assert comparison.old_regime.total_tax_liability >= 0
    assert comparison.new_regime.total_tax_liability >= 0
    assert comparison.estimated_saving >= 0
    assert comparison.recommended_regime in {"old", "new", "equal"}


def test_what_if_scenario_uses_engine_result_without_mutating_profile():
    headers = authenticated_headers()
    profile_payload = {
        "pan_number": unique_pan(),
        "date_of_birth": "1990-01-01",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
        "taxes_paid": [{"tax_type": "tds", "amount": 20000}],
    }
    created = client.post("/api/v1/tax-profiles", headers=headers, json=profile_payload)
    assert created.status_code == 200

    saved_before = client.get("/api/v1/tax-profiles/current", headers=headers)
    original_salary = saved_before.json()["salary_income"][0]["gross_salary"]

    scenario_payload = deepcopy(profile_payload)
    scenario_payload["salary_income"][0]["gross_salary"] = 1500000

    scenario_result = client.post("/api/tax/compare-regimes", json=scenario_payload)
    assert scenario_result.status_code == 200

    saved_after = client.get("/api/v1/tax-profiles/current", headers=headers)
    assert saved_after.json()["salary_income"][0]["gross_salary"] == original_salary
    assert saved_after.json()["salary_income"][0]["gross_salary"] != scenario_payload["salary_income"][0]["gross_salary"]


def test_ai_receives_tax_engine_numbers_in_prompt(monkeypatch):
    headers = authenticated_headers()
    profile_payload = {
        "pan_number": unique_pan(),
        "date_of_birth": "1990-01-01",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
        "taxes_paid": [{"tax_type": "tds", "amount": 20000}],
    }
    created = client.post("/api/v1/tax-profiles", headers=headers, json=profile_payload)
    assert created.status_code == 200

    captured = {}

    class FakeResponses:
        @staticmethod
        def create(**kwargs):
            captured["kwargs"] = kwargs
            return type("FakeCompletion", (), {"output_text": "Explained using the deterministic engine result."})()

    class FakeOpenAI:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.responses = FakeResponses()

    import openai

    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI, raising=False)
    chat_route.OPENAI_API_KEY = "fake-key"
    chat_route.OPENAI_MODEL = "gpt-4o-mini"

    response = client.post("/api/v1/chat", headers=headers, json={"message": "Which regime is better for me?"})

    assert response.status_code == 200
    assert "Explained using the deterministic engine result." in response.json()["answer"]
    assert "old_tax" in str(captured["kwargs"]["input"])
    assert "new_tax" in str(captured["kwargs"]["input"])
    assert "Never invent tax numbers or a final tax result" in captured["kwargs"]["input"][0]["content"]
