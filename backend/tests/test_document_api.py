import os
import uuid
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from reportlab.pdfgen.canvas import Canvas

from main import app


client = TestClient(app)


def pdf_bytes(pan="ABCDE1234F"):
    output = BytesIO()
    canvas = Canvas(output)
    for index, line in enumerate([
        "Employee Name: Diganth H M", f"PAN: {pan}", "Assessment Year: 2026-27",
        "Financial Year: 2025-26", "Employer: Example Technologies Pvt Ltd",
        "Gross Salary: Rs. 8,40,000", "TDS Deducted: Rs. 42,000",
        "Section 80C Investment: Rs. 1,00,000", "Section 80D: Rs. 20,000",
    ]):
        canvas.drawString(40, 780 - index * 24, line)
    canvas.save()
    return output.getvalue()


def headers_for_user():
    email = f"docs-{uuid.uuid4()}@example.com"
    signup = client.post("/api/v1/auth/signup", json={"email": email, "first_name": "Doc", "last_name": "User", "password": "password123"})
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


def test_upload_process_and_confirm_updates_profile():
    headers = headers_for_user()
    pan = "ABCDE" + str(uuid.uuid4().int)[:4] + "F"
    upload = client.post("/api/v1/documents/upload", headers=headers, files={"file": ("TaxWise_Test_Form16.pdf", pdf_bytes(pan), "application/pdf")})
    assert upload.status_code == 202
    document_id = upload.json()["id"]
    processed = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert processed.status_code == 200
    assert processed.json()["status"] == "REQUIRES_CONFIRMATION"
    assert {item["field"] for item in processed.json()["candidates"]} >= {"name", "pan_number", "employer_name", "salary_income", "tds", "deduction_80C", "deduction_80D"}

    candidate = client.post("/api/v1/onboarding/document-candidate", headers=headers, json={"candidate_values": processed.json()["onboarding_values"]})
    assert candidate.status_code == 200
    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    profile = confirmed.json()["profile"]
    assert profile["salary_income"][0]["gross_salary"] in {"840000", "840000.0"}
    assert {item["section"] for item in profile["deductions"]} == {"80C", "80D"}


def test_document_access_is_isolated_by_user():
    owner = headers_for_user()
    other = headers_for_user()
    pan = "ABCDE" + str(uuid.uuid4().int)[:4] + "F"
    upload = client.post("/api/v1/documents/upload", headers=owner, files={"file": ("test.pdf", pdf_bytes(pan), "application/pdf")})
    document_id = upload.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process", headers=other).status_code == 404
    assert all(item["id"] != document_id for item in client.get("/api/v1/documents", headers=other).json())