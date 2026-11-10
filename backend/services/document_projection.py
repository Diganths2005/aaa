import json
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from models.tax_profile import TaxProfile
from models.user import User
from schemas.tax_profile import TaxProfileCreate
from services.profile_service import ProfileService


def candidate_to_profile(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    profile_import = next((item["value"] for item in candidates if item.get("field") == "profile_import"), None)
    if profile_import is not None:
        return json.loads(profile_import) if isinstance(profile_import, str) else profile_import

    candidate_values = {item["field"]: item["value"] for item in candidates if item.get("field")}
    employer = candidate_values.get("employer_name")
    salary = candidate_values.get("salary_income")
    if salary is not None:
        salary_item = {"employer_name": employer or "Document employer", "gross_salary": salary}
        for field in ("standard_deduction", "professional_tax", "tds"):
            if candidate_values.get(field) is not None:
                salary_item[field] = candidate_values[field]
        values["salary_income"] = [salary_item]

    if candidate_values.get("pension_income") is not None:
        values["pension_income"] = [{
            "payer_name": employer or "Document pension payer",
            "amount": candidate_values["pension_income"],
            "tds": candidate_values.get("tds", 0),
        }]

    other_income = []
    for candidate_field, income_type, description in (
        ("other_income_interest", "interest", "Bank interest"),
        ("other_income_dividend", "dividend", "Dividend income"),
        ("other_income_family_pension", "family_pension", "Family pension"),
    ):
        if candidate_values.get(candidate_field) is not None:
            other_income.append({
                "income_type": income_type,
                "description": description,
                "amount": candidate_values[candidate_field],
            })
    if other_income:
        values["other_income"] = other_income

    if any(candidate_values.get(field) is not None for field in (
        "house_property_rent", "house_property_municipal_tax", "house_property_loan_interest"
    )):
        values["house_properties"] = [{
            "property_type": "let_out" if candidate_values.get("house_property_rent") is not None else "self_occupied",
            "city": candidate_values.get("city") or "Document property",
            "annual_rent": candidate_values.get("house_property_rent", 0),
            "municipal_tax": candidate_values.get("house_property_municipal_tax", 0),
            "home_loan_interest": candidate_values.get("house_property_loan_interest", 0),
            "ownership_share": 100,
        }]

    if candidate_values.get("business_net_income") is not None:
        values["business_income"] = [{
            "business_name": "Professional income",
            "nature_of_business": "Professional services",
            "gross_receipts": candidate_values.get("business_receipts", candidate_values["business_net_income"]),
            "net_profit_or_loss": candidate_values["business_net_income"],
        }]

    deductions = []
    for field, section in (
        ("deduction_80C", "80C"), ("deduction_80D", "80D"), ("deduction_80CCD_1B", "80CCD(1B)"),
        ("deduction_80G", "80G"), ("deduction_80E", "80E"), ("deduction_80EE", "80EE"),
        ("deduction_80EEA", "80EEA"), ("deduction_80GG", "80GG"), ("deduction_80U", "80U"),
        ("deduction_80DD", "80DD"), ("deduction_80DDB", "80DDB"),
    ):
        if candidate_values.get(field) is not None:
            deductions.append({"section": section, "amount": candidate_values[field]})
    if deductions:
        values["deductions"] = deductions

    taxes_paid = []
    for field, tax_type in (("tds", "tds"), ("advance_tax", "advance_tax"), ("self_assessment_tax", "self_assessment")):
        if candidate_values.get(field) is not None:
            taxes_paid.append({"tax_type": tax_type, "amount": candidate_values[field]})
    if taxes_paid:
        values["taxes_paid"] = taxes_paid

    for field, profile_field in (
        ("pan_number", "pan_number"), ("date_of_birth", "date_of_birth"), ("name", "name"),
        ("address", "address"), ("employer_name", "employer_name"),
    ):
        if candidate_values.get(field) is not None:
            values[profile_field] = candidate_values[field]
    return jsonable_encoder(values)


def _merge_collection(existing: list[dict[str, Any]], incoming: list[dict[str, Any]], collection: str) -> list[dict[str, Any]]:
    identity_fields = {
        "salary_income": ("employer_name",),
        "pension_income": ("payer_name",),
        "house_properties": ("property_type", "city"),
        "other_income": ("income_type", "description"),
        "capital_gains": ("asset_type", "acquisition_date", "sale_date", "sale_consideration", "acquisition_cost"),
        "business_income": ("business_name",),
        "foreign_income_assets": ("country", "item_type", "description"),
        "investments": ("investment_type",),
        "deductions": ("section",),
        "taxes_paid": ("tax_type", "reference"),
        "bank_accounts": ("bank_name", "account_number"),
    }
    keys = identity_fields.get(collection, ())
    merged = [dict(item) for item in existing]
    for incoming_item in incoming:
        match = next(
            (item for item in merged if keys and all(item.get(key) == incoming_item.get(key) for key in keys)),
            None,
        )
        if match is None:
            if incoming_item not in merged:
                merged.append(dict(incoming_item))
        else:
            match.update(incoming_item)
    return merged


def apply_confirmed_projection(db: Session, user_id: str, values: dict[str, Any]) -> TaxProfile:
    profile_service = ProfileService(db)
    profile = profile_service.get(user_id)
    existing = TaxProfileCreate.model_validate(profile).model_dump(mode="json") if profile else {}
    merged = {**existing, **values}
    for collection in (
        "salary_income", "pension_income", "house_properties", "other_income", "capital_gains",
        "business_income", "foreign_income_assets", "investments", "deductions", "taxes_paid",
        "bank_accounts", "documents",
    ):
        if collection in values and isinstance(values[collection], list):
            merged[collection] = _merge_collection(
                existing.get(collection, []),
                values[collection],
                collection,
            )
    merged.pop("id", None)
    merged.pop("user_id", None)
    validated = TaxProfileCreate.model_validate(merged)
    saved = profile_service.save(user_id, validated, profile_id=profile.id if profile else None)
    if values.get("name"):
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            name_parts = str(values["name"]).split(maxsplit=1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ""
            db.commit()
    return saved


def apply_fact_projection(db: Session, user_id: str, fact_key: str, value: Any, group_id: str | None) -> TaxProfile | None:
    scalar_fields = {
        "personal.pan_number": "pan_number",
        "personal.aadhaar_number": "aadhaar_number",
        "personal.date_of_birth": "date_of_birth",
        "personal.residential_status": "residential_status",
        "personal.employment_type": "employment_type",
        "employment.employer_name": "employer_name",
        "return.is_director": "is_director",
        "return.has_unlisted_equity": "has_unlisted_equity",
        "income.foreign_assets.present": "has_foreign_assets",
        "income.foreign_income.present": "has_foreign_income",
        "income.business.present": "has_business_income",
        "income.speculative.present": "has_speculative_income",
        "loss.carry_forward.present": "has_carry_forward_loss",
        "capital_gains.present": "has_capital_gains",
    }
    profile = ProfileService(db).get(user_id)
    if profile is None:
        current = TaxProfileCreate()
    else:
        current = TaxProfileCreate.model_validate(profile)
    values = current.model_dump(mode="json")
    if fact_key == "capital_gains.transaction" and isinstance(value, dict):
        entries = values.setdefault("capital_gains", [])
        group_parts = group_id.split(":") if group_id else []
        try:
            index = int(group_parts[-1])
        except (ValueError, IndexError):
            index = len(entries)
        if group_id and group_id.startswith("capital_gains:"):
            index = max(index - 1, 0)
        while len(entries) <= index:
            entries.append({})
        entries[index].update(value)
        validated = TaxProfileCreate.model_validate(values)
        return ProfileService(db).save(user_id, validated, profile_id=profile.id if profile else None)
    if fact_key in scalar_fields:
        target = scalar_fields[fact_key]
        if target == "has_capital_gains":
            values["capital_gains"] = values["capital_gains"] if value else []
        else:
            values[target] = value
    else:
        collection_map = {
            "income.salary.": ("salary_income", None),
            "income.pension.": ("pension_income", None),
            "income.house_property.": ("house_properties", None),
            "income.other.": ("other_income", "income_type"),
            "income.business.": ("business_income", None),
            "income.foreign.": ("foreign_income_assets", None),
            "capital_gains.": ("capital_gains", None),
            "deductions.": ("deductions", "section"),
            "taxes.": ("taxes_paid", "tax_type"),
            "investments.": ("investments", None),
            "bank_accounts.": ("bank_accounts", None),
        }
        matched_prefix = next((prefix for prefix in collection_map if fact_key.startswith(prefix)), None)
        if matched_prefix is None:
            return profile
        collection, discriminator = collection_map[matched_prefix]
        parts = fact_key[len(matched_prefix):].split(".")
        if matched_prefix in {"income.other.", "deductions.", "taxes."}:
            discriminator_value, *parts = parts
        else:
            discriminator_value = None
        if not parts:
            return profile
        field = parts[-1]
        entries = values.setdefault(collection, [])
        target = None
        defaults = {
            "salary_income": {"employer_name": "Document employer", "gross_salary": 0, "standard_deduction": 0, "professional_tax": 0, "tds": 0},
            "pension_income": {"payer_name": "Document pension payer", "amount": 0, "tds": 0},
            "house_properties": {"property_type": "self_occupied", "city": "Document property", "annual_rent": 0, "municipal_tax": 0, "home_loan_interest": 0, "ownership_share": 100},
            "other_income": {"income_type": discriminator_value or "other", "description": discriminator_value or "Document income", "amount": 0, "tds": 0},
            "business_income": {"business_name": "Document business", "nature_of_business": "Unspecified", "gross_receipts": 0, "net_profit_or_loss": 0},
            "foreign_income_assets": {"country": "Unspecified", "item_type": "income", "description": "Document fact", "value": 0},
            "capital_gains": {"asset_type": "other_security", "sale_consideration": 0, "acquisition_cost": 0, "improvement_cost": 0, "transfer_expenses": 0},
            "deductions": {"section": discriminator_value or "unknown", "amount": 0},
            "taxes_paid": {"tax_type": discriminator_value or "tds", "amount": 0},
            "investments": {"investment_type": "Document investment", "amount": 0},
            "bank_accounts": {"bank_name": "Unspecified", "account_number": "0000", "ifsc_code": "HDFC0000000", "account_type": "savings", "is_primary": False},
        }
        if group_id:
            group_parts = group_id.split(":")
            try:
                index = int(group_parts[-1])
            except ValueError:
                index = -1
            while index >= 0 and len(entries) <= index:
                entries.append(defaults[collection].copy())
            if 0 <= index < len(entries):
                target = entries[index]
        if target is None and discriminator and discriminator_value is not None:
            target = next((item for item in entries if item.get(discriminator) == discriminator_value), None)
        if target is None and entries and group_id is None:
            target = entries[0]
        if target is None:
            target = defaults[collection].copy()
            entries.append(target)
        target[field] = value
    validated = TaxProfileCreate.model_validate(values)
    return ProfileService(db).save(user_id, validated, profile_id=profile.id if profile else None)
