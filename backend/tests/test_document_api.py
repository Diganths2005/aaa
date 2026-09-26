import os
import uuid
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from openpyxl import Workbook
from reportlab.pdfgen.canvas import Canvas

from main import app


client = TestClient(app)

USED_PANS = set()


def unique_pan():
    while True:
        pan = f"ABCDE{uuid.uuid4().int % 10000:04d}F"
        if pan not in USED_PANS:
            USED_PANS.add(pan)
            return pan


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


def excel_bytes(pan="ABCDE1234F"):
    output = BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Form 16"
    for row in [
        ["Employee Name", "Diganth H M"],
        ["PAN", pan],
        ["Assessment Year", "2026-27"],
        ["Employer", "Example Technologies Pvt Ltd"],
        ["Gross Salary", "840000"],
        ["TDS Deducted", "42000"],
        ["Section 80C Investment", "100000"],
    ]:
        sheet.append(row)
    workbook.save(output)
    return output.getvalue()


def headers_for_user():
    email = f"docs-{uuid.uuid4()}@example.com"
    signup = client.post("/api/v1/auth/signup", json={"email": email, "first_name": "Doc", "last_name": "User", "password": "password123"})
    return {"Authorization": f"Bearer {signup.json()['access_token']}"}


def test_upload_process_and_confirm_updates_profile():
    headers = headers_for_user()
    pan = unique_pan()
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
    pan = unique_pan()
    upload = client.post("/api/v1/documents/upload", headers=owner, files={"file": ("test.pdf", pdf_bytes(pan), "application/pdf")})
    document_id = upload.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process", headers=other).status_code == 404
    assert all(item["id"] != document_id for item in client.get("/api/v1/documents", headers=other).json())


def test_excel_upload_process_and_list_preserves_extracted_values():
    headers = headers_for_user()
    pan = unique_pan()
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("TaxWise_Test_Form16.xlsx", excel_bytes(pan), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 202
    document_id = upload.json()["id"]

    processed = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert processed.status_code == 200
    assert {item["field"] for item in processed.json()["candidates"]} >= {"name", "pan_number", "employer_name", "salary_income", "tds", "deduction_80C"}

    listed = client.get("/api/v1/documents/", headers=headers)
    saved = next(item for item in listed.json() if item["id"] == document_id)
    assert saved["processing_result"]["candidates"]


def test_excel_upload_accepts_browser_generic_mime_type():
    headers = headers_for_user()
    pan = unique_pan()
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("TaxWise_Test_Form16.xlsx", excel_bytes(pan), "application/octet-stream")},
    )
    assert upload.status_code == 202, upload.text
    assert upload.json()["original_filename"] == "TaxWise_Test_Form16.xlsx"