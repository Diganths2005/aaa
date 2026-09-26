import os
import sys
import types
import uuid

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from main import app
from routes import chat as chat_route

chat_route.GEMINI_API_KEY = None

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


def create_profile(headers, **overrides):
    payload = {
        "pan_number": unique_pan(),
        "date_of_birth": "1990-01-01",
        "residential_status": "resident",
        "employment_type": "salaried",
        "salary_income": [{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
        "taxes_paid": [{"tax_type": "tds", "amount": 20000}],
        **overrides,
    }
    response = client.post("/api/v1/tax-profiles", headers=headers, json=payload)
    assert response.status_code == 200


def chat_answer(headers, message):
    response = client.post("/api/v1/chat", headers=headers, json={"message": message})
    assert response.status_code == 200
    return response.json()


def test_chat_explains_zero_deduction_when_none_exist():
    headers = authenticated_headers()
    create_profile(headers)
    answer = chat_answer(headers, "Why is my deduction zero?")["answer"].lower()
    assert "₹0" in answer
    assert "no eligible" in answer
    assert "deductions section" in answer


def test_chat_explains_80c_applied_amount():
    headers = authenticated_headers()
    create_profile(headers, deductions=[{"section": "80C", "amount": 100000}])
    answer = chat_answer(headers, "How much of my 80C deduction was applied?")["answer"]
    assert "80C" in answer
    assert "₹100,000" in answer
    assert "applied" in answer.lower()


def test_chat_explains_80c_rejected_under_new_regime():
    headers = authenticated_headers()
    create_profile(
        headers,
        salary_income=[{"employer_name": "Acme", "gross_salary": 2000000, "standard_deduction": 0, "professional_tax": 0, "tds": 20000}],
        deductions=[{"section": "80C", "amount": 100000}],
    )
    answer = chat_answer(headers, "Why can't I claim 80C?")["answer"].lower()
    assert "80c" in answer
    assert "not available" in answer


def test_chat_explains_rejected_deduction_reason():
    headers = authenticated_headers()
    create_profile(headers, deductions=[{"section": "80CCD(2)", "amount": 50000, "employer_contribution": 50000}])
    answer = chat_answer(headers, "Why can't I claim this deduction?")["answer"].lower()
    assert "80ccd(2)" in answer
    assert "basic salary" in answer


def test_chat_explains_80d_and_multiple_deductions():
    headers = authenticated_headers()
    create_profile(headers, deductions=[
        {"section": "80C", "amount": 100000},
        {"section": "80D", "amount": 0, "self_health_insurance": 20000, "family_health_insurance": 10000},
    ])
    answer = chat_answer(headers, "Explain all my deductions")["answer"]
    assert "80C" in answer
    assert "80D" in answer
    assert "applied" in answer.lower()


def test_chat_uses_deterministic_tax_calculation():
    headers = authenticated_headers()
    create_profile(headers)
    answer = chat_answer(headers, "How much tax do I have to pay?")["answer"]
    assert "tax liability" in answer.lower()
    assert "taxable income" in answer.lower()
    assert "₹" in answer


def test_chat_explains_itr_selection():
    headers = authenticated_headers()
    create_profile(headers, business_income=[{"business_name": "Consulting", "nature_of_business": "Advisory", "gross_receipts": 500000, "net_profit_or_loss": 300000}])
    answer = chat_answer(headers, "Why ITR 3?")["answer"]
    assert "ITR-3" in answer
    assert "business" in answer.lower()


def test_chat_does_not_expose_internal_metadata():
    headers = authenticated_headers()
    create_profile(headers)
    response = chat_answer(headers, "Why is my deduction zero?")
    user_text = response["answer"] + " " + " ".join(response["sources"])
    lowered = user_text.lower()
    for forbidden in ("gemini", "rag", "ay_2026_27.md", "system prompt", "retrieval", "tax engine", "deterministic"):
        assert forbidden not in lowered


def test_chat_keeps_verified_answer_when_model_provider_fails(monkeypatch):
    class FailingClient:
        def __init__(self, **kwargs):
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            raise RuntimeError("provider unavailable")

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = FailingClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setattr(chat_route, "GITHUB_MODELS_TOKENS", ["test-token"])

    headers = authenticated_headers()
    create_profile(headers)
    answer = chat_answer(headers, "How much tax do I have to pay?")

    assert answer["mode"] == "deterministic"
    assert "tax liability" in answer["answer"].lower()
    assert "unable to generate an ai answer" not in answer["answer"].lower()
