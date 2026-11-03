import os
import uuid

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_calculate_endpoint():
    response = client.post("/api/tax/calculate", json={"profile": {"salary_income": [{"employer_name": "Acme", "gross_salary": 1000000}]}, "regime": "new"})
    assert response.status_code == 200
    assert response.json()["regime"] == "new"


def test_compare_regimes_endpoint():
    response = client.post("/api/tax/compare-regimes", json={"salary_income": [{"employer_name": "Acme", "gross_salary": 1000000}]})
    assert response.status_code == 200
    assert response.json()["recommended_regime"] in {"old", "new"}


def test_unsupported_income_returns_structured_error():
    response = client.post("/api/tax/calculate", json={"profile": {"capital_gains": [{"asset_type": "equity", "holding_period": "short_term", "sale_value": 10, "cost_of_acquisition": 5, "gain_or_loss": 5}]}, "regime": "new"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_CAPITAL_GAINS"


def test_invalid_regime_and_assessment_year_return_controlled_errors():
    invalid_regime = client.post(
        "/api/tax/calculate",
        json={"profile": {}, "regime": "unknown"},
    )
    assert invalid_regime.status_code == 422
    assert "regime" in str(invalid_regime.json()["detail"]).lower()

    invalid_year = client.post(
        "/api/tax/calculate",
        json={"profile": {"assessment_year": "2025-26"}, "regime": "new"},
    )
    assert invalid_year.status_code == 422
    assert invalid_year.json()["error"]["code"] == "INVALID_ASSESSMENT_YEAR"


def test_invalid_date_extreme_values_and_unsupported_income_are_rejected():
    invalid_date = client.post(
        "/api/tax/calculate",
        json={
            "profile": {"date_of_birth": "not-a-date"},
            "regime": "old",
        },
    )
    assert invalid_date.status_code == 422

    extreme_amount = client.post(
        "/api/tax/calculate",
        json={
            "profile": {
                "salary_income": [
                    {"employer_name": "Example", "gross_salary": "1E100"}
                ]
            },
            "regime": "new",
        },
    )
    assert extreme_amount.status_code == 422

    unsupported_income = client.post(
        "/api/tax/calculate",
        json={
            "profile": {
                "foreign_income_assets": [
                    {
                        "country": "US",
                        "item_type": "income",
                        "description": "Foreign wages",
                        "value": "1000",
                    }
                ]
            },
            "regime": "new",
        },
    )
    assert unsupported_income.status_code == 422
    assert unsupported_income.json()["error"]["code"] == "UNSUPPORTED_FOREIGN_INCOME"


def test_profile_login_calculation_and_persistence_acceptance_flow():
    email = f"milestone1-{uuid.uuid4()}@example.com"
    password = "password123"
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "first_name": "Milestone",
            "last_name": "Tester",
            "password": password,
        },
    )
    assert signup.status_code == 200
    initial_headers = {"Authorization": f"Bearer {signup.json()['access_token']}"}

    assert client.get("/api/v1/auth/me", headers=initial_headers).status_code == 200
    assert client.get("/api/v1/tax-profiles/current").status_code == 401
    assert client.get("/api/v1/tax-profiles/current", headers=initial_headers).status_code == 404

    created = client.post(
        "/api/v1/tax-profiles/",
        headers=initial_headers,
        json={
            "pan_number": "ABCDE1234F",
            "date_of_birth": "1990-01-15",
            "salary_income": [
                {"employer_name": "Example Ltd", "gross_salary": "1275000.00"}
            ],
            "deductions": [{"section": "80C", "amount": "100000.00"}],
            "taxes_paid": [{"tax_type": "tds", "amount": "3000.00"}],
        },
    )
    assert created.status_code == 200
    profile_id = created.json()["id"]
    assert created.json()["pan_number"] == "AB******4F"

    updated = client.put(
        f"/api/v1/tax-profiles/{profile_id}",
        headers=initial_headers,
        json={
            "salary_income": [
                {"employer_name": "Example Ltd", "gross_salary": "1275000.00"}
            ],
            "deductions": [{"section": "80C", "amount": "150000.00"}],
            "taxes_paid": [{"tax_type": "tds", "amount": "3000.00"}],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["deductions"][0]["amount"] == "150000.00"

    current = client.get("/api/v1/tax-profiles/current", headers=initial_headers)
    assert current.status_code == 200
    calculation_profile = current.json()
    calculation_profile.pop("pan_number")
    comparison = client.post("/api/tax/compare-regimes", json=calculation_profile)
    assert comparison.status_code == 200
    comparison_data = comparison.json()
    assert comparison_data["old_regime"]["total_tax_liability"] == "140400"
    assert comparison_data["new_regime"]["total_tax_liability"] == "0"
    assert comparison_data["recommended_regime"] == "new"

    calculated = client.post(
        "/api/tax/calculate",
        json={"profile": calculation_profile, "regime": "old"},
    )
    assert calculated.status_code == 200
    assert calculated.json()["total_tax_liability"] == comparison_data["old_regime"]["total_tax_liability"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    reauthenticated_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    persisted = client.get(
        "/api/v1/tax-profiles/current",
        headers=reauthenticated_headers,
    )
    assert persisted.status_code == 200
    assert persisted.json()["id"] == profile_id
    assert persisted.json()["salary_income"][0]["gross_salary"] == "1275000.00"
    assert persisted.json()["deductions"][0]["amount"] == "150000.00"

    other_signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": f"other-{uuid.uuid4()}@example.com",
            "first_name": "Other",
            "last_name": "User",
            "password": password,
        },
    )
    other_headers = {"Authorization": f"Bearer {other_signup.json()['access_token']}"}
    assert client.get(
        f"/api/v1/tax-profiles/{profile_id}",
        headers=other_headers,
    ).status_code == 404
    assert client.put(
        f"/api/v1/tax-profiles/{profile_id}",
        headers=other_headers,
        json={"address": "Unauthorized"},
    ).status_code == 404
