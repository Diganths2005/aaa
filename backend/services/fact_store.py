from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from models.taxpayer_fact import TaxpayerFact, TaxpayerFactEvidence
from schemas.tax_profile import TaxProfileCreate
from utils.common import generate_id

FACT_STATUSES = {
    "EXTRACTED",
    "NEEDS_CONFIRMATION",
    "CONFIRMED",
    "REJECTED",
    "SUPERSEDED",
    "CONFLICT",
}

_CANDIDATE_KEYS = {
    "name": ("personal.name", True),
    "pan_number": ("personal.pan_number", True),
    "date_of_birth": ("personal.date_of_birth", True),
    "residential_status": ("personal.residential_status", True),
    "employment_type": ("personal.employment_type", True),
    "employer_name": ("employment.employer_name", True),
    "salary_income": ("income.salary.gross_salary", True),
    "standard_deduction": ("income.salary.standard_deduction", True),
    "professional_tax": ("income.salary.professional_tax", True),
    "tds": ("taxes.tds.amount", True),
    "salary_tds": ("taxes.tds.amount", True),
    "pension_income": ("income.pension.amount", True),
    "house_property_rent": ("income.house_property.annual_rent", True),
    "house_property_municipal_tax": ("income.house_property.municipal_tax", True),
    "house_property_loan_interest": ("income.house_property.home_loan_interest", True),
    "other_income_interest": ("income.other.interest.amount", True),
    "other_income_dividend": ("income.other.dividend.amount", True),
    "business_receipts": ("income.business.gross_receipts", True),
    "business_net_income": ("income.business.net_profit_or_loss", True),
    "advance_tax": ("taxes.advance_tax.amount", True),
    "self_assessment_tax": ("taxes.self_assessment.amount", True),
    "profile_import": ("profile_import", True),
    "capital_gains": ("capital_gains.transaction", True),
}

_DEDUCTION_SECTIONS = {
    "deduction_80C": "80C",
    "deduction_80D": "80D",
    "deduction_80CCD_1B": "80CCD(1B)",
    "deduction_80G": "80G",
    "deduction_80E": "80E",
    "deduction_80EE": "80EE",
    "deduction_80EEA": "80EEA",
    "deduction_80GG": "80GG",
    "deduction_80U": "80U",
    "deduction_80DD": "80DD",
    "deduction_80DDB": "80DDB",
}

_PROFILE_SCALARS = {
    "pan_number": "personal.pan_number",
    "aadhaar_number": "personal.aadhaar_number",
    "date_of_birth": "personal.date_of_birth",
    "residential_status": "personal.residential_status",
    "employment_type": "personal.employment_type",
    "employer_name": "employment.employer_name",
    "is_director": "return.is_director",
    "has_unlisted_equity": "return.has_unlisted_equity",
    "has_foreign_assets": "income.foreign_assets.present",
    "has_foreign_income": "income.foreign_income.present",
    "has_business_income": "income.business.present",
    "has_speculative_income": "income.speculative.present",
    "has_carry_forward_loss": "loss.carry_forward.present",
}

_PROFILE_COLLECTIONS = {
    "salary_income": "income.salary",
    "pension_income": "income.pension",
    "house_properties": "income.house_property",
    "other_income": "income.other",
    "capital_gains": "capital_gains",
    "business_income": "income.business",
    "foreign_income_assets": "income.foreign",
    "investments": "investments",
    "deductions": "deductions",
    "taxes_paid": "taxes",
    "bank_accounts": "bank_accounts",
}


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        try:
            numeric = Decimal(stripped.replace(",", "").replace("₹", "").strip())
            if numeric.is_finite():
                return format(numeric.normalize(), "f")
        except InvalidOperation:
            pass
        return stripped.upper() if len(stripped) == 10 and stripped[:5].isalpha() and stripped[-1].isalpha() else stripped.casefold()
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        try:
            return format(Decimal(str(value)).normalize(), "f")
        except InvalidOperation:
            return str(value)
    if isinstance(value, dict):
        return {key: normalize_value(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


def _candidate_key(field: str) -> tuple[str, str]:
    if field in _DEDUCTION_SECTIONS:
        return f"deductions.{_DEDUCTION_SECTIONS[field]}.amount", "MAPPED"
    mapped = _CANDIDATE_KEYS.get(field)
    if mapped:
        return mapped[0], "MAPPED"
    return f"raw.{field}", "UNMAPPED"


def candidate_fact_key(field: str) -> tuple[str, str]:
    return _candidate_key(field)


def _field_source_text(text: str, page_number: int | None, value: Any) -> str | None:
    if not text:
        return None
    pages = text.split("\f")
    page = pages[page_number - 1] if page_number and 0 < page_number <= len(pages) else text
    candidate = str(value).strip()
    lines = [line.strip() for line in page.splitlines() if line.strip()]
    if candidate:
        exact = next((line for line in lines if candidate.casefold() in line.casefold()), None)
        if exact:
            return exact[:1000]
    return None


def _record_evidence(
    db: Session,
    fact: TaxpayerFact,
    *,
    source_type: str,
    document_id: str | None,
    page_number: int | None,
    section: str | None,
    source_text: str | None,
    confidence: str,
) -> None:
    duplicate = db.query(TaxpayerFactEvidence).filter(
        TaxpayerFactEvidence.fact_id == fact.id,
        TaxpayerFactEvidence.user_id == fact.user_id,
        TaxpayerFactEvidence.document_id == document_id,
        TaxpayerFactEvidence.source_type == source_type,
        TaxpayerFactEvidence.page_number == page_number,
        TaxpayerFactEvidence.source_text == source_text,
    ).first()
    if duplicate:
        return
    db.add(TaxpayerFactEvidence(
        id=generate_id(),
        fact_id=fact.id,
        user_id=fact.user_id,
        source_type=source_type,
        document_id=document_id,
        page_number=page_number,
        section=section,
        source_text=source_text,
        confidence=confidence.upper(),
    ))


def _set_candidate_statuses(
    db: Session,
    *,
    user_id: str,
    assessment_year: str,
    fact_key: str,
    group_id: str | None,
    normalized_value: Any,
    status: str,
) -> None:
    candidates = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.assessment_year == assessment_year,
        TaxpayerFact.fact_key == fact_key,
        TaxpayerFact.group_id == group_id,
        TaxpayerFact.status.in_(("EXTRACTED", "NEEDS_CONFIRMATION", "CONFLICT")),
    ).all()
    for candidate in candidates:
        if candidate.normalized_value == normalized_value:
            candidate.status = status


def _add_extracted_fact(
    db: Session,
    *,
    user_id: str,
    assessment_year: str,
    fact_key: str,
    value: Any,
    source_type: str,
    document_id: str,
    page_number: int | None,
    section: str | None,
    source_text: str | None,
    confidence: str,
    mapping_status: str,
    group_id: str | None,
) -> TaxpayerFact:
    serialized_value = _json_value(value)
    normalized = normalize_value(serialized_value)
    duplicate = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.document_id == document_id,
        TaxpayerFact.assessment_year == assessment_year,
        TaxpayerFact.fact_key == fact_key,
        TaxpayerFact.group_id == group_id,
        TaxpayerFact.normalized_value == normalized,
    ).first()
    if duplicate:
        _record_evidence(
            db, duplicate, source_type=source_type, document_id=document_id,
            page_number=page_number, section=section, source_text=source_text,
            confidence=confidence,
        )
        return duplicate

    existing = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.assessment_year == assessment_year,
        TaxpayerFact.fact_key == fact_key,
        TaxpayerFact.group_id == group_id,
        TaxpayerFact.status.in_(("CONFIRMED", "EXTRACTED", "NEEDS_CONFIRMATION", "CONFLICT")),
    ).all()
    confirmed = [item for item in existing if item.status == "CONFIRMED"]
    if any(item.normalized_value != normalized for item in confirmed):
        fact_status = "CONFLICT"
    else:
        fact_status = "NEEDS_CONFIRMATION"
    fact = TaxpayerFact(
        id=generate_id(),
        user_id=user_id,
        assessment_year=assessment_year,
        fact_key=fact_key,
        value=serialized_value,
        normalized_value=normalized,
        source_type=source_type,
        document_id=document_id,
        page_number=page_number,
        section=section,
        source_text=source_text,
        confidence=confidence.upper(),
        status=fact_status,
        mapping_status=mapping_status,
        group_id=group_id,
    )
    db.add(fact)
    db.flush()
    _record_evidence(
        db, fact, source_type=source_type, document_id=document_id,
        page_number=page_number, section=section, source_text=source_text,
        confidence=confidence,
    )

    other_values = {
        item.normalized_value for item in existing
        if item.status != "CONFIRMED" and item.normalized_value != normalized
    }
    if other_values:
        for item in existing:
            if item.status in {"EXTRACTED", "NEEDS_CONFIRMATION"}:
                item.status = "CONFLICT"
        fact.status = "CONFLICT"
    elif not confirmed:
        peers = [
            item for item in existing
            if item.normalized_value == normalized
            and item.status in {"EXTRACTED", "NEEDS_CONFIRMATION"}
            and item.document_id != document_id
        ]
        independent_sources = {item.source_type for item in peers} | {source_type}
        high_confidence = confidence.lower() == "high" and all(item.confidence.upper() == "HIGH" for item in peers)
        if len(independent_sources) >= 2 and high_confidence:
            _set_candidate_statuses(
                db, user_id=user_id, assessment_year=assessment_year,
                fact_key=fact_key, group_id=group_id,
                normalized_value=normalized, status="CONFIRMED",
            )
            fact.status = "CONFIRMED"
    return fact


def persist_extracted_candidates(
    db: Session,
    *,
    user_id: str,
    assessment_year: str,
    document_id: str,
    candidates: list[dict[str, Any]],
    extracted_text: str,
) -> list[TaxpayerFact]:
    facts: list[TaxpayerFact] = []
    for candidate in candidates:
        field = str(candidate.get("field", "")).strip()
        if not field:
            continue
        key, mapping_status = _candidate_key(field)
        page_number = candidate.get("page")
        confidence = str(candidate.get("confidence", "low")).upper()
        value = candidate.get("value")
        source_type = str(candidate.get("source") or "DOCUMENT").upper()
        source_text = _field_source_text(extracted_text, page_number, value)
        section = field.replace("_", " ")
        values = value if field == "capital_gains" and isinstance(value, list) else [value]
        for index, item in enumerate(values):
            group_id = f"{field}:{index + 1}" if field == "capital_gains" and isinstance(value, list) else None
            facts.append(_add_extracted_fact(
                db,
                user_id=user_id,
                assessment_year=assessment_year,
                fact_key=key,
                value=item,
                source_type=source_type,
                document_id=document_id,
                page_number=page_number,
                section=section,
                source_text=source_text,
                confidence=confidence,
                mapping_status=mapping_status,
                group_id=group_id,
            ))
        if field == "profile_import":
            imported = value
            if isinstance(imported, str):
                try:
                    imported = json.loads(imported)
                except json.JSONDecodeError:
                    imported = None
            if isinstance(imported, dict):
                facts.extend(_persist_imported_profile(
                    db,
                    user_id=user_id,
                    assessment_year=assessment_year,
                    document_id=document_id,
                    profile=imported,
                    source_type=source_type,
                    page_number=page_number,
                    source_text=source_text,
                    confidence=confidence,
                ))
    return facts


def _persist_imported_profile(
    db: Session,
    *,
    user_id: str,
    assessment_year: str,
    document_id: str,
    profile: dict[str, Any],
    source_type: str,
    page_number: int | None,
    source_text: str | None,
    confidence: str,
) -> list[TaxpayerFact]:
    facts = []
    for field, key in _PROFILE_SCALARS.items():
        if field in profile:
            facts.append(_add_extracted_fact(
                db, user_id=user_id, assessment_year=assessment_year,
                fact_key=key, value=profile[field], source_type=source_type,
                document_id=document_id, page_number=page_number, section=field,
                source_text=source_text, confidence=confidence,
                mapping_status="MAPPED", group_id=None,
            ))
    for collection, prefix in _PROFILE_COLLECTIONS.items():
        for index, entry in enumerate(profile.get(collection, []) or []):
            if not isinstance(entry, dict):
                facts.append(_add_extracted_fact(
                    db, user_id=user_id, assessment_year=assessment_year,
                    fact_key=f"raw.profile_import.{collection}.{index}",
                    value=entry, source_type=source_type, document_id=document_id,
                    page_number=page_number, section=collection, source_text=source_text,
                    confidence=confidence, mapping_status="UNMAPPED",
                    group_id=f"import:{collection}:{index}",
                ))
                continue
            if collection == "other_income":
                record_prefix = f"income.other.{entry.get('income_type', 'other')}"
            elif collection == "deductions":
                record_prefix = f"deductions.{entry.get('section', 'unknown')}"
            elif collection == "taxes_paid":
                record_prefix = f"taxes.{entry.get('tax_type', 'other')}"
            else:
                record_prefix = prefix
            group_id = f"import:{collection}:{index}" if index else None
            for field, entry_value in entry.items():
                facts.append(_add_extracted_fact(
                    db, user_id=user_id, assessment_year=assessment_year,
                    fact_key=f"{record_prefix}.{field}", value=entry_value,
                    source_type=source_type, document_id=document_id,
                    page_number=page_number, section=collection, source_text=source_text,
                    confidence=confidence, mapping_status="MAPPED", group_id=group_id,
                ))
    return facts


def _add_user_fact(
    db: Session,
    *,
    user_id: str,
    assessment_year: str,
    fact_key: str,
    value: Any,
    group_id: str | None = None,
) -> TaxpayerFact:
    normalized = normalize_value(value)
    current = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.assessment_year == assessment_year,
        TaxpayerFact.fact_key == fact_key,
        TaxpayerFact.group_id == group_id,
        TaxpayerFact.status == "CONFIRMED",
    ).all()
    same = next((item for item in current if item.normalized_value == normalized), None)
    if same:
        _record_evidence(
            db, same, source_type="USER", document_id=None,
            page_number=None, section="Tax Profile",
            source_text="Entered or reviewed in Tax Profile", confidence="HIGH",
        )
        return same
    for item in current:
        item.status = "SUPERSEDED"
    fact = TaxpayerFact(
        id=generate_id(),
        user_id=user_id,
        assessment_year=assessment_year,
        fact_key=fact_key,
        value=_json_value(value),
        normalized_value=normalized,
        source_type="USER",
        confidence="HIGH",
        status="CONFIRMED",
        mapping_status="MAPPED",
        group_id=group_id,
    )
    db.add(fact)
    db.flush()
    _record_evidence(
        db, fact, source_type="USER", document_id=None,
        page_number=None, section="Tax Profile",
        source_text="Entered or reviewed in Tax Profile", confidence="HIGH",
    )
    return fact


def record_profile_facts(db: Session, user_id: str, profile: TaxProfileCreate) -> None:
    payload = profile.model_dump(mode="json")
    assessment_year = profile.assessment_year
    for field, key in _PROFILE_SCALARS.items():
        value = payload.get(field)
        if value is not None:
            _add_user_fact(db, user_id=user_id, assessment_year=assessment_year, fact_key=key, value=value)

    for collection, prefix in _PROFILE_COLLECTIONS.items():
        entries = payload.get(collection, [])
        if collection.startswith(("salary", "pension", "house", "other", "capital", "business", "foreign")):
            _add_user_fact(
                db,
                user_id=user_id,
                assessment_year=assessment_year,
                fact_key=f"{prefix}.present",
                value=bool(entries),
            )
        for index, entry in enumerate(entries or []):
            group_id = f"profile:{collection}:{index}" if index else None
            if collection == "other_income":
                prefix_for_entry = f"income.other.{entry.get('income_type', 'other')}"
            elif collection == "deductions":
                prefix_for_entry = f"deductions.{entry.get('section', 'unknown')}"
            elif collection == "taxes_paid":
                prefix_for_entry = f"taxes.{entry.get('tax_type', 'other')}"
            else:
                prefix_for_entry = prefix
            for field, value in entry.items():
                if value is None:
                    continue
                _add_user_fact(
                    db,
                    user_id=user_id,
                    assessment_year=assessment_year,
                    fact_key=f"{prefix_for_entry}.{field}",
                    value=value,
                    group_id=group_id,
                )
    db.flush()


def backfill_legacy_profile_facts(db: Session, user_id: str, profile: TaxProfileCreate) -> None:
    if db.query(TaxpayerFact.id).filter(TaxpayerFact.user_id == user_id).first():
        return
    payload = profile.model_dump(mode="json")
    values: list[tuple[str, Any, str | None]] = []
    for field, key in _PROFILE_SCALARS.items():
        if payload.get(field) is not None:
            values.append((key, payload[field], None))
    for collection, prefix in _PROFILE_COLLECTIONS.items():
        entries = payload.get(collection, []) or []
        if collection.startswith(("salary", "pension", "house", "other", "capital", "business", "foreign")):
            values.append((f"{prefix}.present", bool(entries), None))
        for index, entry in enumerate(entries):
            group_id = f"profile:{collection}:{index}" if index else None
            if collection == "other_income":
                record_prefix = f"income.other.{entry.get('income_type', 'other')}"
            elif collection == "deductions":
                record_prefix = f"deductions.{entry.get('section', 'unknown')}"
            elif collection == "taxes_paid":
                record_prefix = f"taxes.{entry.get('tax_type', 'other')}"
            else:
                record_prefix = prefix
            values.extend(
                (f"{record_prefix}.{field}", value, group_id)
                for field, value in entry.items()
                if value is not None
            )
    for fact_key, value, group_id in values:
        fact = TaxpayerFact(
            id=generate_id(),
            user_id=user_id,
            assessment_year=profile.assessment_year,
            fact_key=fact_key,
            value=_json_value(value),
            normalized_value=normalize_value(value),
            source_type="LEGACY_PROFILE",
            confidence="LOW",
            status="NEEDS_CONFIRMATION",
            mapping_status="MAPPED",
            group_id=group_id,
        )
        db.add(fact)
        db.flush()
        _record_evidence(
            db, fact, source_type="LEGACY_PROFILE", document_id=None,
            page_number=None, section="Saved Tax Profile",
            source_text="Imported from a saved profile; original provenance is unavailable.",
            confidence="LOW",
        )


def facts_for_document(db: Session, user_id: str, document_id: str) -> list[TaxpayerFact]:
    return db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.document_id == document_id,
    ).order_by(TaxpayerFact.created_at, TaxpayerFact.fact_key).all()


def reconcile_facts(db: Session, user_id: str, assessment_year: str) -> list[dict[str, Any]]:
    facts = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.assessment_year == assessment_year,
        TaxpayerFact.status.notin_(("REJECTED", "SUPERSEDED")),
    ).order_by(TaxpayerFact.fact_key, TaxpayerFact.created_at).all()
    grouped: dict[tuple[str, str | None], list[TaxpayerFact]] = {}
    for fact in facts:
        grouped.setdefault((fact.fact_key, fact.group_id), []).append(fact)
    results = []
    for (fact_key, group_id), items in grouped.items():
        values: dict[str, list[TaxpayerFact]] = {}
        for item in items:
            fingerprint = json.dumps(item.normalized_value, sort_keys=True, ensure_ascii=True)
            values.setdefault(fingerprint, []).append(item)
        conflicting = len(values) > 1
        results.append({
            "fact_key": fact_key,
            "group_id": group_id,
            "status": "CONFLICT" if conflicting else items[-1].status,
            "agreement_count": max((len(group) for group in values.values()), default=0),
            "values": [
                {
                    "value": group[0].value,
                    "fact_ids": [fact.id for fact in group],
                    "sources": sorted({fact.source_type for fact in group}),
                    "statuses": sorted({fact.status for fact in group}),
                }
                for group in values.values()
            ],
        })
    return results


def _requirement_status(facts: list[TaxpayerFact]) -> str:
    active = [fact for fact in facts if fact.status not in {"REJECTED", "SUPERSEDED"}]
    if not active:
        return "MISSING"
    if any(fact.status == "CONFLICT" for fact in active):
        return "CONFLICT"
    if any(fact.status in {"NEEDS_CONFIRMATION", "EXTRACTED"} for fact in active):
        return "NEEDS_CONFIRMATION"
    if all(fact.status == "CONFIRMED" for fact in active):
        return "CONFIRMED"
    return "MISSING"


def readiness_report(db: Session, user_id: str, assessment_year: str) -> dict[str, Any]:
    facts = db.query(TaxpayerFact).filter(
        TaxpayerFact.user_id == user_id,
        TaxpayerFact.assessment_year == assessment_year,
    ).all()
    requirements: list[dict[str, Any]] = []
    definitions = (
        ("personal.pan_number", "PAN", "Personal information"),
        ("personal.date_of_birth", "Date of birth", "Personal information"),
        ("personal.residential_status", "Residential status", "Personal information"),
        ("personal.employment_type", "Employment status", "Personal information"),
    )
    for key, label, section in definitions:
        matches = [fact for fact in facts if fact.fact_key == key]
        requirements.append(_make_requirement(key, label, section, matches))

    active_facts = [fact for fact in facts if fact.status not in {"REJECTED", "SUPERSEDED"}]
    income_keys = {
        "income.salary.gross_salary",
        "income.pension.amount",
        "income.other.interest.amount",
        "income.other.dividend.amount",
        "income.business.net_profit_or_loss",
        "income.house_property.annual_rent",
        "capital_gains.transaction",
    }
    income_facts = [fact for fact in active_facts if fact.fact_key in income_keys]
    requirements.append(_make_requirement("income_source", "At least one income source", "Income", income_facts, require_any=True))

    known_requirements: dict[str, tuple[str, str]] = {}
    for fact in active_facts:
        if fact.mapping_status != "MAPPED":
            continue
        if fact.fact_key.startswith("income.salary."):
            known_requirements.setdefault(fact.fact_key, (fact.fact_key.rsplit(".", 1)[-1].replace("_", " ").title(), "Salary"))
        elif fact.fact_key.startswith("income.house_property."):
            known_requirements.setdefault(fact.fact_key, (fact.fact_key.rsplit(".", 1)[-1].replace("_", " ").title(), "House property"))
        elif fact.fact_key.startswith("income.other.") or fact.fact_key.startswith("income.pension.") or fact.fact_key.startswith("income.business.") or fact.fact_key.startswith("income.foreign.") or fact.fact_key.startswith("capital_gains."):
            known_requirements.setdefault(fact.fact_key, (fact.fact_key.rsplit(".", 1)[-1].replace("_", " ").title(), "Income"))
        elif fact.fact_key.startswith(("deductions.", "taxes.", "return.", "loss.", "bank_accounts.")):
            known_requirements.setdefault(fact.fact_key, (fact.fact_key.rsplit(".", 1)[-1].replace("_", " ").title(), "Deductions and taxes"))
    for key, (label, section) in known_requirements.items():
        if key in {item[0] for item in definitions}:
            continue
        matches = [fact for fact in active_facts if fact.fact_key == key]
        if matches and key.endswith(".present") and all(fact.value is False for fact in matches if fact.status == "CONFIRMED"):
            requirements.append(_make_requirement(key, label, section, matches, applicable=False))
            continue
        requirements.append(_make_requirement(key, label, section, matches))

    applicable = [item for item in requirements if item["applicable"] and item["required"]]
    confirmed = sum(item["status"] == "CONFIRMED" for item in applicable)
    percent = round(confirmed * 100 / len(applicable)) if applicable else 0
    missing = [item for item in applicable if item["status"] != "CONFIRMED"]
    return {
        "assessment_year": assessment_year,
        "readiness_percent": percent,
        "ready": bool(applicable) and not missing,
        "requirements": requirements,
        "missing": missing,
    }


def _make_requirement(
    key: str,
    label: str,
    section: str,
    facts: list[TaxpayerFact],
    *,
    applicable: bool = True,
    require_any: bool = False,
) -> dict[str, Any]:
    status = "NOT_APPLICABLE" if not applicable else _requirement_status(facts)
    evidence_ids = []
    if facts:
        evidence_ids = [
            evidence.id
            for fact in facts
            for evidence in fact.evidence
        ]
    value = facts[0].value if len(facts) == 1 else None
    if value is not None and any(part in key.casefold() for part in ("pan", "aadhaar", "account_number")):
        value_text = str(value)
        value = f"******{value_text[-4:]}" if value_text else value
    return {
        "key": key,
        "label": label,
        "section": section,
        "applicable": applicable,
        "required": applicable,
        "status": status,
        "value": value,
        "fact_ids": [fact.id for fact in facts],
        "evidence_ids": evidence_ids,
        "resolution_action": "confirm_or_resolve" if status in {"NEEDS_CONFIRMATION", "CONFLICT"} else ("enter_value" if status == "MISSING" else None),
        "requires_any": require_any,
    }
