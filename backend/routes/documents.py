from pathlib import Path
from tempfile import gettempdir

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from database import get_db
from documents.extractor import process_pdf
from documents.spreadsheet_extractor import process_spreadsheet
from models.document import UserDocument
from models.user import User
from routes.auth import get_current_user
from schemas.document import DocumentCreate, DocumentResponse, DocumentType, SUPPORTED_DOCUMENT_EXTENSIONS
from utils.common import generate_id

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
DOCUMENT_STORAGE = Path(gettempdir()) / "taxwise-documents"
DOCUMENT_STORAGE.mkdir(exist_ok=True)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
def register_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register optional document metadata; binary storage and processing are future adapters."""
    document = UserDocument(
        id=generate_id(),
        user_id=current_user.id,
        **document_data.model_dump(),
        status="UPLOADED",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = "other",
    assessment_year: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filename = file.filename or "document.pdf"
    extension = Path(filename).suffix.lower()
    supported_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/octet-stream",
    }
    allowed_excel_mime_types = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel.sheet.macroEnabled.12",
        "application/octet-stream",
    }
    is_pdf = extension == ".pdf" and file.content_type in {"application/pdf"} or extension == ".pdf" and file.content_type is None
    is_excel = extension in {".xlsx", ".xlsm"} and (
        file.content_type in allowed_excel_mime_types or file.content_type in {None, "application/octet-stream"}
    )
    if extension not in SUPPORTED_DOCUMENT_EXTENSIONS or not (is_pdf or is_excel):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a PDF or Excel workbook (.xlsx, .xlsm)")
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Documents must be 10 MB or smaller")
    storage_extension = ".pdf" if extension == ".pdf" else ".xlsx"
    document = UserDocument(
        id=generate_id(), user_id=current_user.id, document_type=document_type,
        original_filename=filename, assessment_year=assessment_year,
        status="UPLOADED", storage_key=f"{generate_id()}{storage_extension}",
    )
    (DOCUMENT_STORAGE / document.storage_key).write_bytes(content)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post("/{document_id}/process")
def process_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(UserDocument).filter(UserDocument.id == document_id, UserDocument.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not document.storage_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document content is not available for processing")
    storage_path = DOCUMENT_STORAGE / Path(document.storage_key).name
    if not storage_path.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document content is not available for processing")
    document.status = "PROCESSING"
    db.commit()
    try:
        content = storage_path.read_bytes()
        result = process_pdf(content) if storage_path.suffix.lower() == ".pdf" else process_spreadsheet(content)
        candidates = [candidate.as_dict() for candidate in result.candidates]
        onboarding_values = _onboarding_values(candidates)
        document.status = "REQUIRES_CONFIRMATION" if candidates else "PROCESSED"
        document.page_count = result.page_count
        document.processing_result = {"document_type": result.document_type, "candidates": candidates, "onboarding_values": onboarding_values}
        db.commit()
        return {"document_id": document.id, "status": document.status, "page_count": result.page_count, "candidates": candidates, "onboarding_values": onboarding_values}
    except ValueError as exc:
        document.status = "FAILED"
        document.processing_result = {"error": str(exc)}
        db.commit()
        if str(exc) == "DOCUMENT_REQUIRES_OCR":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="DOCUMENT_REQUIRES_OCR") from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Could not extract text from this PDF") from exc


def _onboarding_values(candidates: list[dict]) -> dict:
    values = {}
    candidate_values = {item["field"]: item["value"] for item in candidates}
    salary = next((item["value"] for item in candidates if item["field"] == "salary_income"), None)
    tds = next((item["value"] for item in candidates if item["field"] == "tds"), None)
    employer = next((item["value"] for item in candidates if item["field"] == "employer_name"), None)
    pan = next((item["value"] for item in candidates if item["field"] == "pan_number"), None)
    date_of_birth = next((item["value"] for item in candidates if item["field"] == "date_of_birth"), None)
    name = next((item["value"] for item in candidates if item["field"] == "name"), None)
    if salary is not None:
        values["salary_income"] = [{"employer_name": employer or "Document employer", "gross_salary": salary, "standard_deduction": 0, "professional_tax": 0, "tds": 0}]
    if tds is not None:
        values["salary_tds"] = tds
    if candidate_values.get("business_net_income") is not None:
        values["business_income"] = [{
            "business_name": "Professional income",
            "nature_of_business": "Professional services",
            "gross_receipts": candidate_values.get("business_receipts", candidate_values["business_net_income"]),
            "net_profit_or_loss": candidate_values["business_net_income"],
        }]
    other_income = []
    if candidate_values.get("other_income_interest") is not None:
        other_income.append({"income_type": "interest", "description": "Bank interest", "amount": candidate_values["other_income_interest"], "tds": 0})
    if candidate_values.get("other_income_dividend") is not None:
        other_income.append({"income_type": "dividend", "description": "Dividend income", "amount": candidate_values["other_income_dividend"], "tds": 0})
    if other_income:
        values["other_income"] = other_income
    if employer is not None:
        values["employer_name"] = employer
    if pan is not None:
        values["pan_number"] = pan
    if date_of_birth is not None:
        values["date_of_birth"] = date_of_birth
    if name is not None:
        values["name"] = name
    deductions = [{"section": section, "amount": candidate_values.get(field)} for field, section in (("deduction_80C", "80C"), ("deduction_80D", "80D"), ("deduction_80CCD_1B", "80CCD(1B)"))]
    values["deductions"] = [item for item in deductions if item["amount"] is not None]
    taxes_paid = []
    if tds is not None:
        taxes_paid.append({"tax_type": "tds", "amount": tds})
    if candidate_values.get("advance_tax") is not None:
        taxes_paid.append({"tax_type": "advance_tax", "amount": candidate_values["advance_tax"]})
    if taxes_paid:
        values["taxes_paid"] = taxes_paid
    return jsonable_encoder(values)


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(UserDocument).filter(UserDocument.user_id == current_user.id).order_by(UserDocument.created_at.desc()).all()


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.user_id == current_user.id,
    ).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(document)
    if document.storage_key:
        (DOCUMENT_STORAGE / Path(document.storage_key).name).unlink(missing_ok=True)
    db.commit()