import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from documents.extractor import process_pdf
from documents.spreadsheet_extractor import process_spreadsheet
from models.document import UserDocument, UserDocumentChunk
from models.user import User
from routes.auth import get_current_user
from schemas.document import DocumentCreate, DocumentResponse, DocumentType, SUPPORTED_DOCUMENT_EXTENSIONS
from services.knowledge import chunk_text
from services.document_storage import DocumentStorage
from utils.common import generate_id

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
DOCUMENT_STORAGE = DocumentStorage()


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
    document_id = generate_id()
    document = UserDocument(
        id=document_id, user_id=current_user.id, document_type=document_type,
        original_filename=filename, assessment_year=assessment_year,
        status="UPLOADED",
    )
    storage_key, content_sha256 = DOCUMENT_STORAGE.save(
        current_user.id, document_id, f"{document_id}{storage_extension}", content
    )
    document.storage_key = storage_key
    document.metadata_json = {"content_sha256": content_sha256, "size_bytes": len(content)}
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
    try:
        storage_path = DOCUMENT_STORAGE.path_for(document.storage_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid document storage key") from exc
    if not storage_path.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document content is not available for processing")
    if document.status in {"PROCESSED", "REQUIRES_CONFIRMATION", "CONFIRMED"} and document.processing_result:
        result_data = document.processing_result
        return {
            "document_id": document.id,
            "status": document.status,
            "page_count": document.page_count,
            "candidates": result_data.get("candidates", []),
            "onboarding_values": result_data.get("onboarding_values", {}),
        }

    document.status = "PROCESSING"
    document.processing_result = None
    db.commit()
    try:
        content = storage_path.read_bytes()
        stored_hash = (document.metadata_json or {}).get("content_sha256")
        if stored_hash and stored_hash != DOCUMENT_STORAGE.sha256(content):
            raise ValueError("Stored document content changed unexpectedly")
        result = process_pdf(content) if storage_path.suffix.lower() == ".pdf" else process_spreadsheet(content)
        candidates = [candidate.as_dict() for candidate in result.candidates]
        onboarding_values = _onboarding_values(candidates)
        extracted_pages = result.text.split("\f") if storage_path.suffix.lower() == ".pdf" else [result.text]
        db.query(UserDocumentChunk).filter(UserDocumentChunk.document_id == document.id).delete(synchronize_session=False)
        chunks = []
        chunk_index = 0
        for page_number, page_text in enumerate(extracted_pages, start=1):
            for text in chunk_text(page_text):
                chunks.append(UserDocumentChunk(
                    id=generate_id(),
                    document_id=document.id,
                    chunk_index=chunk_index,
                    page_number=page_number,
                    text=text,
                ))
                chunk_index += 1
        db.add_all(chunks)
        document.status = "REQUIRES_CONFIRMATION" if candidates else "PROCESSED"
        document.page_count = result.page_count
        document.processing_result = {"document_type": result.document_type, "candidates": candidates, "onboarding_values": onboarding_values}
        db.commit()
        return {"document_id": document.id, "status": document.status, "page_count": result.page_count, "candidates": candidates, "onboarding_values": onboarding_values}
    except ValueError as exc:
        db.query(UserDocumentChunk).filter(UserDocumentChunk.document_id == document.id).delete(synchronize_session=False)
        document.status = "FAILED"
        document.processing_result = {"error": str(exc)}
        db.commit()
        if str(exc) == "DOCUMENT_REQUIRES_OCR":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="DOCUMENT_REQUIRES_OCR") from exc
        detail = "Could not extract text from this PDF" if storage_path.suffix.lower() == ".pdf" else str(exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc


def _onboarding_values(candidates: list[dict]) -> dict:
    values = {}
    profile_import = next((item["value"] for item in candidates if item["field"] == "profile_import"), None)
    if profile_import is not None:
        return json.loads(profile_import)
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
    deductions = [{"section": section, "amount": candidate_values.get(field)} for field, section in (("deduction_80C", "80C"), ("deduction_80D", "80D"), ("deduction_80CCD_1B", "80CCD(1B)"), ("deduction_80G", "80G"))]
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


@router.get("/{document_id}/content")
def get_document_content(
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
    if not document.storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document content is not available")
    storage_path = DOCUMENT_STORAGE / Path(document.storage_key).name
    if not storage_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document content is not available")
    media_type = "application/pdf" if storage_path.suffix.lower() == ".pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(
        content=storage_path.read_bytes(),
        media_type=media_type,
        headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store"},
    )


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
    db.query(UserDocumentChunk).filter(UserDocumentChunk.document_id == document.id).delete(synchronize_session=False)
    db.delete(document)
    if document.storage_key:
        try:
            DOCUMENT_STORAGE.delete(document.storage_key)
        except ValueError:
            pass
    db.commit()