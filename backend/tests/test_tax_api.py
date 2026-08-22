import os

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
