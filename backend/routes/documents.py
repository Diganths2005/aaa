from pathlib import Path
from tempfile import gettempdir

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from database import get_db
from documents.extractor import process_pdf
from models.document import UserDocument
from models.user import User
from routes.auth import get_current_user
from schemas.document import DocumentCreate, DocumentResponse, DocumentType
from utils.common import generate_id

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_PDF_BYTES = 10 * 1024 * 1024
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
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF documents are supported")
    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="PDF must be 10 MB or smaller")
    document = UserDocument(
        id=generate_id(), user_id=current_user.id, document_type=document_type,
        original_filename=file.filename or "document.pdf", assessment_year=assessment_year,
        status="UPLOADED", storage_key=f"{generate_id()}.pdf",
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
        result = process_pdf(storage_path.read_bytes())
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
    salary = next((item["value"] for item in candidates if item["field"] == "salary_income"), None)
    tds = next((item["value"] for item in candidates if item["field"] == "tds"), None)
    employer = next((item["value"] for item in candidates if item["field"] == "employer_name"), None)
    pan = next((item["value"] for item in candidates if item["field"] == "pan_number"), None)
    name = next((item["value"] for item in candidates if item["field"] == "name"), None)
    if salary is not None:
        values["salary_income"] = [{"employer_name": employer or "Document employer", "gross_salary": salary, "standard_deduction": 0, "professional_tax": 0, "tds": 0}]
    if tds is not None:
        values["salary_tds"] = tds
    if employer is not None:
        values["employer_name"] = employer
    if pan is not None:
        values["pan_number"] = pan
    if name is not None:
        values["name"] = name
    deductions = [{"section": section, "amount": next((item["value"] for item in candidates if item["field"] == field), None)} for field, section in (("deduction_80C", "80C"), ("deduction_80D", "80D"))]
    values["deductions"] = [item for item in deductions if item["amount"] is not None]
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