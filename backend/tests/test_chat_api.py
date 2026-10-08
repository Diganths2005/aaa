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


def test_chat_answers_knowledge_question_with_assessment_year_source():
    headers = authenticated_headers()
    response = client.post("/api/v1/chat", headers=headers, json={"message": "How does the rebate work under the new regime?"})

    assert response.status_code == 200
    assert "rebate" in response.json()["answer"].lower()
    assert "regime is currently better" not in response.json()["answer"].lower()
    assert "section 87a" in response.json()["answer"].lower()
    assert "#" not in response.json()["answer"]
    assert "concepts/rebate.md" in response.json()["sources"]


def test_chat_refuses_tax_questions_outside_knowledge_scope(monkeypatch):
    class UnexpectedClient:
        def __init__(self, **kwargs):
            raise AssertionError("unsupported questions must not reach the model provider")

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = UnexpectedClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setattr(chat_route, "GITHUB_MODELS_TOKENS", ["test-token"])
    headers = authenticated_headers()
    response = client.post("/api/v1/chat", headers=headers, json={"message": "How is cryptocurrency taxed?"})

    assert response.status_code == 200
    assert "outside" in response.json()["answer"].lower()
    assert response.json()["sources"] == []


def test_knowledge_lookup_failure_does_not_break_deterministic_tax_answer(monkeypatch):
    def fail_retrieval(self, query, filters, limit=5):
        raise OSError("knowledge files unavailable")

    monkeypatch.setattr(chat_route.LocalTaxKnowledgeBase, "retrieve", fail_retrieval)
    headers = authenticated_headers()
    create_profile(headers)

    response = chat_answer(headers, "How much tax do I have to pay?")

    assert response["mode"] == "deterministic"
    assert "tax liability" in response["answer"].lower()


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


def test_chat_explains_tax_amount_from_engine_breakdown():
    headers = authenticated_headers()
    create_profile(headers)

    response = chat_answer(headers, "Why is my tax this amount?")
    answer = response["answer"].lower()

    for stage in ("gross total income", "deductions", "taxable income", "slab calculation", "rebate", "cess", "final tax liability", "taxes already paid", "refund", "payable"):
        assert stage in answer


def test_chat_uses_engine_facts_for_taxable_income_and_tds():
    headers = authenticated_headers()
    create_profile(headers)

    taxable_income = chat_answer(headers, "What is my taxable income?")["answer"]
    tds = chat_answer(headers, "How much TDS have I paid?")["answer"]

    assert "taxable income" in taxable_income.lower()
    assert "₹" in taxable_income
    assert "₹20,000" in tds


def test_chat_answers_profile_salary_rebate_and_cess_from_engine():
    headers = authenticated_headers()
    create_profile(headers)

    salary = chat_answer(headers, "How much salary is in my profile?")["answer"]
    rebate = chat_answer(headers, "What is my rebate?")["answer"]
    cess = chat_answer(headers, "What is my cess?")["answer"]

    assert "₹1,000,000" in salary
    assert "rebate" in rebate.lower() and "₹" in rebate
    assert "cess" in cess.lower() and "₹" in cess


def test_chat_reports_salary_source_tds_when_no_tax_payment_entry_exists():
    headers = authenticated_headers()
    create_profile(
        headers,
        salary_income=[{"employer_name": "Acme", "gross_salary": 1000000, "standard_deduction": 0, "professional_tax": 0, "tds": 25000}],
        taxes_paid=[],
    )

    answer = chat_answer(headers, "How much TDS is recorded?")["answer"]

    assert "₹25,000" in answer


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
    for forbidden in ("gemini", "system prompt", "retrieval", "tax engine", "deterministic"):
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


def test_chat_rejects_model_answer_with_unverified_amount(monkeypatch):
    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            return type("FakeCompletion", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "Your calculated tax liability is ₹999,999. The confirmed profile and deterministic calculation support this explanation, and no further action is needed before filing your return."})()})()]})()

    class FakeClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": FakeCompletions})()

    monkeypatch.setattr(chat_route, "GITHUB_MODELS_TOKENS", ["fake-token"])
    monkeypatch.setattr("openai.OpenAI", FakeClient)
    headers = authenticated_headers()
    create_profile(headers)

    response = chat_answer(headers, "How much tax do I have to pay?")

    assert response["mode"] == "deterministic"
    assert "₹999,999" not in response["answer"]
    assert "tax liability" in response["answer"].lower()
