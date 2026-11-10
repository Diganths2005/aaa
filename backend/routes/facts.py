import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from itr.service import select_return
from models.document import UserDocument, UserDocumentChunk
from models.tax_profile import TaxProfile
from models.taxpayer_fact import TaxpayerFact, TaxpayerFactEvidence
from models.user import User
from routes.auth import get_current_user
from schemas.facts import DocumentFactResolutionRequest, FactResolutionRequest
from schemas.tax_profile import TaxProfileCreate
from services.document_projection import apply_confirmed_projection, apply_fact_projection, candidate_to_profile
from services.fact_store import (
    _record_evidence,
    candidate_fact_key,
    backfill_legacy_profile_facts,
    facts_for_document,
    normalize_value,
    record_profile_facts,
    readiness_report,
    reconcile_facts,
)
from utils.common import generate_id

router = APIRouter(prefix="/facts", tags=["taxpayer-facts"])

_PAN = re.compile(r"\b([A-Z]{2})[A-Z]{3}\d{4}([A-Z])\b", re.IGNORECASE)
_AADHAAR = re.compile(r"\b(?:\d[\s-]?){12}\b")
_ACCOUNT = re.compile(r"(?i)(account(?:\s+(?:number|no\.?))?[\s:#-]*)(\d{6,18})")


def _mask_text(value: Any) -> Any:
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            if any(part in str(key).casefold() for part in ("pan", "aadhaar", "account_number")) and item is not None:
                raw = str(item)
                masked[key] = f"******{raw[-4:]}" if raw else item
            else:
                masked[key] = _mask_text(item)
        return masked
    if isinstance(value, list):
        return [_mask_text(item) for item in value]
    if not isinstance(value, str):
        return value
    value = _PAN.sub(lambda match: f"{match.group(1)}******{match.group(2)}", value)
    value = _AADHAAR.sub(lambda match: "********" + re.sub(r"\D", "", match.group(0))[-4:], value)
    value = _ACCOUNT.sub(lambda match: f"{match.group(1)}******{match.group(2)[-4:]}", value)
    return value


def _serialized_fact(fact: TaxpayerFact, document_names: dict[str, str]) -> dict[str, Any]:
    sensitive_key = any(part in fact.fact_key.casefold() for part in ("pan", "aadhaar", "account_number"))
    value = fact.value
    normalized_value = fact.normalized_value
    if sensitive_key:
        raw = str(value)
        value = f"******{raw[-4:]}" if raw else value
        normalized_value = value
    evidence = []
    for item in fact.evidence:
        evidence.append({
            "id": item.id,
            "source_type": item.source_type,
            "document_id": item.document_id,
            "document_name": document_names.get(item.document_id) if item.document_id else None,
            "page_number": item.page_number,
            "section": item.section,
            "source_text": _mask_text(item.source_text),
            "confidence": item.confidence,
        })
    return {
        "id": fact.id,
        "assessment_year": fact.assessment_year,
        "fact_key": fact.fact_key,
        "value": _mask_text(value),
        "normalized_value": _mask_text(normalized_value),
        "source_type": fact.source_type,
        "document_id": fact.document_id,
        "document_name": document_names.get(fact.document_id) if fact.document_id else None,
        "page_number": fact.page_number,
        "section": fact.section,
        "source_text": _mask_text(fact.source_text),
        "confidence": fact.confidence,
        "status": fact.status,
        "mapping_status": fact.mapping_status,
        "group_id": fact.group_id,
        "evidence": evidence,
    }


def _document_names(db: Session, user_id: str, facts: list[TaxpayerFact]) -> dict[str, str]:
    ids = {fact.document_id for fact in facts if fact.document_id}
    if not ids:
        return {}
    documents = db.query(UserDocument).filter(
        UserDocument.user_id == user_id,
        UserDocument.id.in_(ids),
    ).all()
    return {document.id: document.original_filename for document in documents}


def _sync_document_statuses(db: Session, user_id: str, document_ids: set[str]) -> None:
    for document_id in document_ids:
        document = db.query(UserDocument).filter(
            UserDocument.id == document_id,
            UserDocument.user_id == user_id,
        ).first()
        if not document:
            continue
        facts = facts_for_document(db, user_id, document_id)
        if not facts:
            continue
        if any(fact.status not in {"CONFIRMED", "REJECTED", "SUPERSEDED"} for fact in facts):
            document.status = "REQUIRES_CONFIRMATION"
        else:
            document.status = "CONFIRMED" if any(fact.status == "CONFIRMED" for fact in facts) else "REJECTED"


def _owned_fact(db: Session, user_id: str, fact_id: str) -> TaxpayerFact:
    fact = db.query(TaxpayerFact).filter(
        TaxpayerFact.id == fact_id,
        TaxpayerFact.user_id == user_id,
    ).first()
    if not fact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")
    return fact


@router.get("/")
def list_facts(
    assessment_year: str = "2026-27",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if profile and not db.query(TaxpayerFact.id).filter(TaxpayerFact.user_id == current_user.id).first():
        backfill_legacy_profile_facts(db, current_user.id, TaxProfileCreate.model_validate(profile))
        db.commit()
    facts = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == current_user.id,
        TaxpayerFact.assessment_year == assessment_year,
        TaxpayerFact.status != "SUPERSEDED",
    ).order_by(TaxpayerFact.created_at.desc(), TaxpayerFact.fact_key).all()
    names = _document_names(db, current_user.id, facts)
    return [_serialized_fact(fact, names) for fact in facts]


@router.get("/reconciliation")
def get_reconciliation(
    assessment_year: str = "2026-27",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = reconcile_facts(db, current_user.id, assessment_year)
    for result in results:
        for item in result["values"]:
            sensitive_key = any(part in result["fact_key"].casefold() for part in ("pan", "aadhaar", "account_number"))
            if sensitive_key and item["value"] is not None:
                value = str(item["value"])
                item["value"] = f"******{value[-4:]}" if value else value
            else:
                item["value"] = _mask_text(item["value"])
    return results


@router.get("/readiness")
def get_readiness(
    assessment_year: str = "2026-27",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if profile and not db.query(TaxpayerFact.id).filter(TaxpayerFact.user_id == current_user.id).first():
        backfill_legacy_profile_facts(db, current_user.id, TaxProfileCreate.model_validate(profile))
        db.commit()
    return readiness_report(db, current_user.id, assessment_year)


@router.get("/determination")
def get_determination(
    assessment_year: str = "2026-27",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(TaxProfile).filter(TaxProfile.user_id == current_user.id).first()
    if profile and not db.query(TaxpayerFact.id).filter(TaxpayerFact.user_id == current_user.id).first():
        backfill_legacy_profile_facts(db, current_user.id, TaxProfileCreate.model_validate(profile))
        db.commit()
    readiness = readiness_report(db, current_user.id, assessment_year)
    if not profile:
        return {
            "status": "NEEDS_REVIEW",
            "recommended_itr": None,
            "reasons": ["A confirmed Tax Profile projection is not available."],
            "readiness": readiness,
        }
    selection = select_return(TaxProfileCreate.model_validate(profile))
    return {
        "status": "SUPPORTED" if selection.preparation_supported else "NEEDS_REVIEW",
        "recommended_itr": selection.recommended_itr,
        "eligible": selection.eligible,
        "preparation_supported": selection.preparation_supported,
        "reasons": selection.reasons,
        "missing_information": selection.missing_information,
        "unsupported_conditions": selection.unsupported_conditions,
        "readiness": readiness,
    }


@router.post("/{fact_id}/resolve")
def resolve_fact(
    fact_id: str,
    request: FactResolutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fact = _owned_fact(db, current_user.id, fact_id)
    related = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == current_user.id,
        TaxpayerFact.assessment_year == fact.assessment_year,
        TaxpayerFact.fact_key == fact.fact_key,
        TaxpayerFact.group_id == fact.group_id,
        TaxpayerFact.status.notin_(("REJECTED", "SUPERSEDED")),
    ).all()
    confirmed = [item for item in related if item.status == "CONFIRMED"]

    if request.action == "confirm":
        if any(item.normalized_value != fact.normalized_value for item in confirmed):
            fact.status = "CONFLICT"
            db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A confirmed fact has a different value. Choose keep or accept to resolve the conflict.")
        if fact.status not in {"EXTRACTED", "NEEDS_CONFIRMATION", "CONFLICT"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This fact cannot be confirmed in its current state.")
        fact.status = "CONFIRMED"
    elif request.action == "reject":
        if fact.status in {"CONFIRMED", "SUPERSEDED"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmed facts cannot be rejected; add a correction instead.")
        fact.status = "REJECTED"
    elif request.action == "keep":
        if fact.status != "CONFLICT" or not confirmed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="There is no confirmed value to keep for this conflict.")
        for item in related:
            if item.status in {"CONFLICT", "EXTRACTED", "NEEDS_CONFIRMATION"}:
                item.status = "REJECTED"
    elif request.action == "accept":
        if fact.status != "CONFLICT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a conflicting candidate can replace a confirmed fact.")
        for item in related:
            if item.id != fact.id and item.status in {"CONFIRMED", "CONFLICT", "EXTRACTED", "NEEDS_CONFIRMATION"}:
                item.status = "SUPERSEDED" if item.status == "CONFIRMED" else "REJECTED"
        fact.status = "CONFIRMED"
    else:
        if request.value is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A corrected fact value is required.")
        if len(str(request.value)) > 10000:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The corrected value is too large.")
        for item in related:
            item.status = "SUPERSEDED"
        correction = TaxpayerFact(
            id=generate_id(),
            user_id=current_user.id,
            assessment_year=fact.assessment_year,
            fact_key=fact.fact_key,
            value=request.value,
            normalized_value=normalize_value(request.value),
            source_type="USER",
            document_id=fact.document_id,
            confidence="HIGH",
            status="CONFIRMED",
            mapping_status=fact.mapping_status,
            group_id=fact.group_id,
        )
        db.add(correction)
        db.flush()
        _record_evidence(
            db, correction, source_type="USER", document_id=None,
            page_number=None, section="Taxpayer correction",
            source_text="Corrected by taxpayer", confidence="HIGH",
        )
        fact = correction
    if request.action in {"confirm", "accept", "correct"} and fact.status == "CONFIRMED" and fact.mapping_status == "MAPPED":
        from pydantic import ValidationError

        try:
            apply_fact_projection(db, current_user.id, fact.fact_key, fact.value, fact.group_id)
        except ValidationError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error.errors(),
            ) from error
    db.commit()
    document_ids = {item.document_id for item in related if item.document_id}
    if fact.document_id:
        document_ids.add(fact.document_id)
    if document_ids:
        _sync_document_statuses(db, current_user.id, document_ids)
        db.commit()
    db.refresh(fact)
    names = _document_names(db, current_user.id, [fact])
    return {"fact": _serialized_fact(fact, names), "readiness": readiness_report(db, current_user.id, fact.assessment_year)}


@router.post("/documents/{document_id}/resolve")
def resolve_document_facts(
    document_id: str,
    request: DocumentFactResolutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.user_id == current_user.id,
    ).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    facts = facts_for_document(db, current_user.id, document.id)
    if not facts:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This document has no persisted facts to review.")

    if request.action == "reject":
        for fact in facts:
            if fact.status not in {"CONFIRMED", "SUPERSEDED"}:
                fact.status = "REJECTED"
        db.query(UserDocumentChunk).filter(UserDocumentChunk.document_id == document.id).delete(synchronize_session=False)
        document.status = "REJECTED"
    else:
        for fact in facts:
            if fact.status not in {"EXTRACTED", "NEEDS_CONFIRMATION"}:
                continue
            conflicting_confirmed = db.query(TaxpayerFact).filter(
                TaxpayerFact.user_id == current_user.id,
                TaxpayerFact.assessment_year == fact.assessment_year,
                TaxpayerFact.fact_key == fact.fact_key,
                TaxpayerFact.group_id == fact.group_id,
                TaxpayerFact.status == "CONFIRMED",
                TaxpayerFact.normalized_value != fact.normalized_value,
            ).first()
            fact.status = "CONFLICT" if conflicting_confirmed else "CONFIRMED"
        unresolved = [fact for fact in facts if fact.status in {"CONFLICT", "EXTRACTED", "NEEDS_CONFIRMATION"}]
        document.status = "REQUIRES_CONFIRMATION" if unresolved else "CONFIRMED"
        candidates = (document.processing_result or {}).get("candidates", [])
        safe_candidates = []
        for candidate in candidates:
            fact_key, _ = candidate_fact_key(str(candidate.get("field", "")))
            matching = [
                fact for fact in facts
                if fact.fact_key == fact_key
                or (candidate.get("field") == "profile_import" and fact.group_id and fact.group_id.startswith("import:"))
            ]
            if matching and all(fact.status == "CONFIRMED" for fact in matching):
                safe_candidates.append(candidate)
        if safe_candidates:
            profile_values = candidate_to_profile(safe_candidates)
            if profile_values:
                profile = apply_confirmed_projection(db, current_user.id, profile_values)
                record_profile_facts(db, current_user.id, TaxProfileCreate.model_validate(profile))
    db.commit()
    facts = facts_for_document(db, current_user.id, document.id)
    names = _document_names(db, current_user.id, facts)
    return {
        "document_id": document.id,
        "status": document.status,
        "facts": [_serialized_fact(fact, names) for fact in facts],
        "conflicts": [fact.id for fact in facts if fact.status == "CONFLICT"],
        "readiness": readiness_report(db, current_user.id, document.assessment_year or "2026-27"),
    }
