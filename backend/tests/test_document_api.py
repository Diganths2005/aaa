import os
import sys
import types
import uuid
from io import BytesIO

os.environ["DATABASE_URL"] = "sqlite:///./tax-api-test.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient
from openpyxl import Workbook
from reportlab.pdfgen.canvas import Canvas

from database import SessionLocal
from main import app
from models.document import UserDocumentChunk
from routes import chat as chat_route


client = TestClient(app)

USED_PANS = set()


def unique_pan():
    while True:
        entropy = uuid.uuid4().int
        letters = "".join(chr(65 + ((entropy >> (index * 5)) % 26)) for index in range(5))
        pan = f"{letters}{entropy % 10000:04d}F"
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

    candidate = client.post("/api/v1/onboarding/document-candidate", headers=headers, json={"candidate_values": processed.json()["onboarding_values"], "document_id": document_id})
    assert candidate.status_code == 200
    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    profile = confirmed.json()["profile"]
    assert profile["salary_income"][0]["gross_salary"] in {"840000", "840000.0"}
    assert profile["salary_income"][0]["tds"] in {"42000", "42000.0"}
    assert {item["section"] for item in profile["deductions"]} == {"80C", "80D"}
    listed = client.get("/api/v1/documents/", headers=headers)
    assert next(item for item in listed.json() if item["id"] == document_id)["status"] == "CONFIRMED"


def test_taxwise_import_template_populates_supported_profile_fields_after_confirmation():
    headers = headers_for_user()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "TaxWise Import Data"
    for row in [
        ["TaxWise document import data", "", ""],
        ["Instructions", "", "Enter actual values in column B."],
        ["Exact importer label", "Your value", "What to enter"],
        ["Employee Name", "Example Taxpayer", "Name as shown in PAN records."],
        ["PAN", unique_pan(), "Sensitive."],
        ["Date of Birth", "15-06-1990", "DD-MM-YYYY."],
        ["Employer", "Example Employer", "Form 16."],
        ["Gross Salary", "840000", "INR."],
        ["TDS Deducted", "42000", "Form 16 / Form 26AS."],
        ["Professional Receipts", "2400000", "INR."],
        ["Net Professional Income", "1700000", "Reviewed book profit."],
        ["Bank Interest", "30000", "INR."],
        ["Dividend Income", "10000", "INR."],
        ["Section 80C", "100000", "Supported claim."],
        ["Section 80D", "20000", "Supported claim."],
        ["80CCD(1B)", "50000", "Supported claim."],
        ["Section 80G", "5000", "Supported claim."],
        ["Advance Tax", "50000", "Challan / Form 26AS."],
    ]:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    pan = sheet["B5"].value

    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("TaxWise_App_Import_Template.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 202
    document_id = upload.json()["id"]
    processed = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert processed.status_code == 200
    assert processed.json()["status"] == "REQUIRES_CONFIRMATION"
    assert {item["field"] for item in processed.json()["candidates"]} == {
        "name", "pan_number", "date_of_birth", "employer_name", "salary_income", "tds",
        "business_receipts", "business_net_income", "other_income_interest", "other_income_dividend",
        "deduction_80C", "deduction_80D", "deduction_80CCD_1B", "deduction_80G", "advance_tax",
    }

    candidate = client.post(
        "/api/v1/onboarding/document-candidate",
        headers=headers,
        json={"candidate_values": processed.json()["onboarding_values"], "document_id": document_id},
    )
    assert candidate.status_code == 200
    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    profile = confirmed.json()["profile"]
    assert profile["pan_number"] == f"{pan[:2]}******{pan[-2:]}"
    assert profile["date_of_birth"] == "1990-06-15"
    assert profile["salary_income"][0]["employer_name"] == "Example Employer"
    assert profile["salary_income"][0]["gross_salary"] in {"840000", "840000.0"}
    assert profile["salary_income"][0]["tds"] in {"42000", "42000.0"}
    assert profile["business_income"][0]["gross_receipts"] in {"2400000", "2400000.0"}
    assert profile["business_income"][0]["net_profit_or_loss"] in {"1700000", "1700000.0"}
    assert {item["section"] for item in profile["deductions"]} == {"80C", "80D", "80CCD(1B)", "80G"}
    assert {item["tax_type"] for item in profile["taxes_paid"]} == {"tds", "advance_tax"}


def test_full_profile_workbook_imports_profile_records_after_confirmation():
    headers = headers_for_user()
    workbook = Workbook()
    scalar = workbook.active
    scalar.title = "TaxWise Profile Import"
    scalar.append(["Title"])
    scalar.append(["Instructions"])
    scalar.append(["Profile field", "Your value", "Guidance"])
    scalar.append(["taxpayer_name", "Full Profile Taxpayer", ""])
    scalar.append(["pan_number", unique_pan(), ""])
    scalar.append(["address", "10 Example Road", ""])
    scalar.append(["residential_status", "resident", ""])

    salary = workbook.create_sheet("salary_income")
    salary.append(["Title"])
    salary.append(["One row per employer"])
    salary.append(["employer_name", "gross_salary", "standard_deduction", "professional_tax", "tds"])
    salary.append(["Example Employer", 1200000, 75000, 2500, 60000])

    gains = workbook.create_sheet("capital_gains")
    gains.append(["Title"])
    gains.append(["One row per disposal"])
    gains.append(["asset_type", "acquisition_date", "sale_date", "sale_consideration", "acquisition_cost"])
    gains.append(["listed_equity_share", "2023-04-01", "2025-12-01", 150000, 100000])

    deductions = workbook.create_sheet("deductions")
    deductions.append(["Title"])
    deductions.append(["One row per claim"])
    deductions.append(["section", "amount"])
    deductions.append(["80C", 100000])

    taxes = workbook.create_sheet("taxes_paid")
    taxes.append(["Title"])
    taxes.append(["One row per payment"])
    taxes.append(["tax_type", "amount", "reference"])
    taxes.append(["advance_tax", 25000, "CHALLAN-123"])

    banks = workbook.create_sheet("bank_accounts")
    banks.append(["Title"])
    banks.append(["Sensitive account details; keep private"])
    banks.append(["bank_name", "account_number", "ifsc_code", "account_type", "is_primary"])
    banks.append(["Example Bank", "1234567890", "ABCD0123456", "savings", "Yes"])

    output = BytesIO()
    workbook.save(output)
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={
            "file": (
                "TaxWise_App_Import_Template.xlsx",
                output.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert upload.status_code == 202
    document_id = upload.json()["id"]
    processed = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)
    assert processed.status_code == 200
    assert processed.json()["status"] == "REQUIRES_CONFIRMATION"
    assert [candidate["field"] for candidate in processed.json()["candidates"]] == ["profile_import"]

    candidate = client.post(
        "/api/v1/onboarding/document-candidate",
        headers=headers,
        json={"candidate_values": processed.json()["onboarding_values"], "document_id": document_id},
    )
    assert candidate.status_code == 200
    confirmed = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "confirm"})
    assert confirmed.status_code == 200
    profile = confirmed.json()["profile"]
    assert profile["address"] == "10 Example Road"
    assert profile["salary_income"][0]["gross_salary"] == "1200000"
    assert profile["capital_gains"][0]["sale_consideration"] == "150000"
    assert profile["deductions"][0]["section"] == "80C"
    assert profile["taxes_paid"][0]["reference"] == "CHALLAN-123"
    assert profile["bank_accounts"][0]["account_number"] == "******7890"


def test_rejected_document_candidates_do_not_change_profile_and_are_not_reoffered():
    headers = headers_for_user()
    upload = client.post("/api/v1/documents/upload", headers=headers, files={"file": ("test.pdf", pdf_bytes(unique_pan()), "application/pdf")})
    document_id = upload.json()["id"]
    processed = client.post(f"/api/v1/documents/{document_id}/process", headers=headers)

    candidate = client.post("/api/v1/onboarding/document-candidate", headers=headers, json={
        "candidate_values": processed.json()["onboarding_values"],
        "document_id": document_id,
    })
    assert candidate.status_code == 200
    rejected = client.post("/api/v1/onboarding/confirm", headers=headers, json={"action": "reject"})
    assert rejected.status_code == 200
    assert client.get("/api/v1/tax-profiles/current", headers=headers).status_code == 404
    saved = next(item for item in client.get("/api/v1/documents/", headers=headers).json() if item["id"] == document_id)
    assert saved["status"] == "REJECTED"
    lookup = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "What does my uploaded Form 16 say about gross salary?"},
    )
    assert lookup.json()["sources"] == []
    with SessionLocal() as db:
        assert db.query(UserDocumentChunk).filter(
            UserDocumentChunk.document_id == document_id
        ).count() == 0


def test_document_access_is_isolated_by_user():
    owner = headers_for_user()
    other = headers_for_user()
    pan = unique_pan()
    document_content = pdf_bytes(pan)
    upload = client.post("/api/v1/documents/upload", headers=owner, files={"file": ("test.pdf", document_content, "application/pdf")})
    document_id = upload.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process", headers=other).status_code == 404
    assert client.get(f"/api/v1/documents/{document_id}/content", headers=owner).content == document_content
    assert client.get(f"/api/v1/documents/{document_id}/content", headers=other).status_code == 404
    assert all(item["id"] != document_id for item in client.get("/api/v1/documents", headers=other).json())


def test_chat_retrieves_only_the_current_users_processed_document(monkeypatch):
    owner = headers_for_user()
    other = headers_for_user()
    upload = client.post(
        "/api/v1/documents/upload",
        headers=owner,
        files={"file": ("Private_Form16.pdf", pdf_bytes(unique_pan()), "application/pdf")},
    )
    document_id = upload.json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process", headers=owner).status_code == 200
    provider_attempts = []

    class UnexpectedClient:
        def __init__(self, **kwargs):
            provider_attempts.append(True)
            raise AssertionError("private document content must not be sent to a hosted model")

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=UnexpectedClient))
    monkeypatch.setattr(chat_route, "GITHUB_MODELS_TOKENS", ["test-token"])

    question = "What does my uploaded Form 16 say about gross salary?"
    owner_answer = client.post("/api/v1/chat", headers=owner, json={"message": question})
    other_answer = client.post("/api/v1/chat", headers=other, json={"message": question})

    assert owner_answer.status_code == 200
    assert "8,40,000" in owner_answer.json()["answer"]
    assert "Private_Form16.pdf (page 1)" in owner_answer.json()["sources"]
    assert other_answer.status_code == 200
    assert "outside" in other_answer.json()["answer"].lower()
    assert other_answer.json()["sources"] == []
    assert provider_attempts == []


def test_deleting_document_removes_it_from_chat_retrieval():
    headers = headers_for_user()
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": ("Private_Form16.pdf", pdf_bytes(unique_pan()), "application/pdf")},
    )
    document_id = upload.json()["id"]
    client.post(f"/api/v1/documents/{document_id}/process", headers=headers)

    assert client.delete(f"/api/v1/documents/{document_id}", headers=headers).status_code == 204
    response = client.post(
        "/api/v1/chat",
        headers=headers,
        json={"message": "What does my uploaded Form 16 say about gross salary?"},
    )

    assert response.status_code == 200
    assert response.json()["sources"] == []


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