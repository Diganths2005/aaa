from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from itr.service import select_return
from schemas.tax_profile import TaxProfileCreate


@dataclass(frozen=True)
class ReadinessItem:
    key: str
    section: str
    label: str
    required: bool
    complete: bool
    reason: str = ""


def _item(key: str, section: str, label: str, required: bool, complete: bool, reason: str = "") -> ReadinessItem:
    return ReadinessItem(key, section, label, required, complete, reason)


def build_return_readiness(profile: TaxProfileCreate) -> dict[str, Any]:
    """
    Return-family-aware completeness checklist.

    Inspired by itr-agent's separation of form selection from filing readiness:
    select_return() decides the family; this service decides whether the data
    represented in the TaxWise profile is sufficient for the supported path.

    It deliberately does not treat empty optional income heads as missing.
    Once an income head exists, its records are validated field-by-field.
    """
    selection = select_return(profile)
    items: list[ReadinessItem] = []

    # Part A / general information needed across supported individual returns.
    items.extend([
        _item("pan", "Personal", "PAN", True, bool(profile.pan_number)),
        _item("dob", "Personal", "Date of birth", True, bool(profile.date_of_birth)),
        _item("residential_status", "Personal", "Residential status", True, bool(profile.residential_status)),
        _item("address", "Personal", "Primary address", True, bool(profile.address and profile.city and profile.state and profile.pincode)),
        _item("bank", "Taxes & banks", "At least one bank account", True, bool(profile.bank_accounts)),
    ])

    # Income heads: only applicable heads become required.
    for index, salary in enumerate(profile.salary_income, 1):
        items.extend([
            _item(f"salary.{index}.employer", "Salary", f"Employer #{index}", True, bool(salary.employer_name)),
            _item(f"salary.{index}.gross", "Salary", f"Gross salary #{index}", True, salary.gross_salary >= Decimal("0")),
        ])

    for index, pension in enumerate(profile.pension_income, 1):
        items.extend([
            _item(f"pension.{index}.payer", "Pension", f"Pension payer #{index}", True, bool(pension.payer_name)),
            _item(f"pension.{index}.amount", "Pension", f"Pension amount #{index}", True, pension.amount >= Decimal("0")),
        ])

    for index, prop in enumerate(profile.house_properties, 1):
        items.extend([
            _item(f"house.{index}.type", "House property", f"Property type #{index}", True, bool(prop.property_type)),
            _item(f"house.{index}.location", "House property", f"Property location #{index}", True, bool(prop.city)),
            _item(f"house.{index}.ownership", "House property", f"Ownership share #{index}", True, prop.ownership_share > 0),
        ])
        if prop.property_type in {"let_out", "deemed_let_out"}:
            items.extend([
                _item(f"house.{index}.rent", "House property", f"Annual rent #{index}", True, prop.annual_rent >= Decimal("0")),
                _item(f"house.{index}.municipal", "House property", f"Municipal tax #{index}", True, prop.municipal_tax >= Decimal("0")),
            ])
        if prop.home_loan_interest > 0:
            items.append(
                _item(
                    f"house.{index}.loan",
                    "House property",
                    f"Home-loan interest details #{index}",
                    True,
                    bool(prop.loan_purpose and prop.loan_sanction_date and prop.construction_completed_within_five_years is not None),
                    "The tax engine needs loan purpose, sanction date and completion information when interest is claimed.",
                )
            )

    for index, other in enumerate(profile.other_income, 1):
        items.extend([
            _item(f"other.{index}.type", "Other income", f"Income type #{index}", True, bool(other.income_type)),
            _item(f"other.{index}.description", "Other income", f"Description #{index}", True, bool(other.description)),
            _item(f"other.{index}.amount", "Other income", f"Amount #{index}", True, other.amount >= Decimal("0")),
        ])

    for index, gain in enumerate(profile.capital_gains, 1):
        base_complete = bool(
            gain.acquisition_date
            and gain.sale_date
            and gain.sale_consideration is not None
            and gain.acquisition_cost is not None
        )
        items.append(
            _item(
                f"capital_gain.{index}.core",
                "Capital gains",
                f"Transaction #{index} core details",
                True,
                base_complete,
                "Acquisition date, sale date, sale consideration and acquisition cost are required for the supported capital-gain path.",
            )
        )
        if gain.is_listed is True:
            items.append(
                _item(
                    f"capital_gain.{index}.stt",
                    "Capital gains",
                    f"Listed-equity/STT details #{index}",
                    True,
                    gain.stt_paid_on_transfer is not None,
                    "Listed-equity transactions need the applicable STT/transaction classification before special-rate treatment.",
                )
            )
        if gain.asset_type == "immovable_property":
            items.append(
                _item(
                    f"capital_gain.{index}.property_costs",
                    "Capital gains",
                    f"Property improvement and transfer costs #{index}",
                    True,
                    gain.improvement_cost >= 0 and gain.transfer_expenses >= 0,
                )
            )

    for index, business in enumerate(profile.business_income, 1):
        items.extend([
            _item(f"business.{index}.name", "Business", f"Business name #{index}", True, bool(business.business_name)),
            _item(f"business.{index}.nature", "Business", f"Nature of business #{index}", True, bool(business.nature_of_business)),
            _item(f"business.{index}.receipts", "Business", f"Gross receipts #{index}", True, business.gross_receipts >= 0),
            _item(f"business.{index}.profit", "Business", f"Net profit/loss #{index}", True, business.net_profit_or_loss >= 0),
        ])

    for index, foreign in enumerate(profile.foreign_income_assets, 1):
        items.extend([
            _item(f"foreign.{index}.country", "Foreign assets/income", f"Country #{index}", True, bool(foreign.country)),
            _item(f"foreign.{index}.type", "Foreign assets/income", f"Asset/income type #{index}", True, bool(foreign.item_type)),
            _item(f"foreign.{index}.description", "Foreign assets/income", f"Description #{index}", True, bool(foreign.description)),
            _item(f"foreign.{index}.value", "Foreign assets/income", f"Value #{index}", True, foreign.value >= 0),
        ])

    for index, deduction in enumerate(profile.deductions, 1):
        complete = bool(deduction.section) and deduction.amount >= 0
        reason = ""
        if deduction.section == "80C":
            complete = complete and bool(deduction.policy_or_document_id)
            if not deduction.policy_or_document_id:
                reason = "80C requires the policy number or document identification number."
        elif deduction.section in {"80CCD(1)", "80CCD(1B)"}:
            complete = complete and bool(deduction.pran)
            if not deduction.pran:
                reason = f"{deduction.section} requires the taxpayer's PRAN."
        elif deduction.section == "80D":
            complete = complete and bool(deduction.insurer_name) and bool(deduction.insurance_policy_number)
            if not complete:
                reason = "80D requires insurer name and policy number."
        elif deduction.section in {"80E", "80EE", "80EEA", "80EEB"}:
            complete = complete and bool(deduction.loan_institution) and bool(deduction.loan_account_number) and bool(deduction.loan_sanction_date)
            if not complete:
                reason = f"{deduction.section} requires loan institution/account and sanction details."
        elif deduction.section == "80GG":
            complete = complete and bool(deduction.form_10ba_acknowledgement)
            if not deduction.form_10ba_acknowledgement:
                reason = "80GG requires the Form 10BA acknowledgement number."
        elif deduction.section == "80G":
            if deduction.donation_amount > 0:
                complete = complete and bool(deduction.donee_pan) and bool(deduction.donation_transaction_reference) and bool(deduction.donation_ifsc)
                if not complete:
                    reason = "80G requires donee PAN plus transaction reference and IFSC for the AY 2026-27 Schedule 80G workflow."
        elif deduction.section == "80GGC":
            complete = complete and bool(deduction.donee_name) and bool(deduction.donee_pan)
            if not complete:
                reason = "80GGC requires political party name and PAN."
        elif deduction.section in {"80DD", "80U"}:
            complete = complete and bool(deduction.disability_type) and bool(deduction.form_10ia_acknowledgement)
            if not complete:
                reason = f"{deduction.section} requires disability details and Form 10-IA acknowledgement information."
        items.append(_item(f"deduction.{index}", "Deductions", f"Deduction #{index} ({deduction.section})", True, complete, reason))

    if profile.taxes_paid:
        for index, payment in enumerate(profile.taxes_paid, 1):
            items.append(
                _item(
                    f"tax.{index}",
                    "Taxes & banks",
                    f"Tax payment #{index} ({payment.tax_type})",
                    True,
                    payment.amount >= 0,
                )
            )
    elif profile.salary_income or profile.pension_income or profile.other_income:
        recorded_tds = sum(
            (item.tds for item in (*profile.salary_income, *profile.pension_income, *profile.other_income)),
            Decimal("0"),
        )
        items.append(
            _item(
                "tax.tds_confirmation",
                "Taxes & banks",
                "TDS / tax-payment information",
                True,
                recorded_tds > 0,
                "Enter tax payments or explicitly confirm that no TDS/tax payment applies.",
            )
        )

    # Document readiness follows the same idea as itr-agent's filing checklist:
    # the return can be prepared from confirmed data, but missing evidence should
    # remain visible instead of being converted into invented zeros.
    document_types = {document.document_type for document in profile.documents}
    if profile.salary_income:
        items.append(_item("doc.form16", "Documents", "Salary evidence / Form 16", False, "form_16" in document_types,
                            "ITR-2 guidance lists Form 16 for salary income."))
    if profile.other_income and any(item.tds > 0 for item in profile.other_income):
        items.append(_item("doc.form16a", "Documents", "TDS evidence for non-salary income", False, "form_26as" in document_types or "other" in document_types,
                            "ITR-2 guidance calls for Form 16A where TDS is deducted on interest."))
    if profile.capital_gains:
        items.append(_item("doc.capital_gains", "Documents", "Capital-gains statement/evidence", False, "investment" in document_types or "other" in document_types,
                            "ITR-2 guidance calls for a capital-gains summary/profit-loss statement."))
    if profile.house_properties and any(p.property_type in {"let_out", "deemed_let_out"} for p in profile.house_properties):
        items.append(_item("doc.house_property", "Documents", "House-property supporting evidence", False, "other" in document_types,
                            "ITR-2 guidance calls for rent, local-tax and borrowed-capital details where applicable."))

    required = [item for item in items if item.required]
    complete = [item for item in required if item.complete]
    missing = [item for item in required if not item.complete]

    percentage = round((len(complete) / len(required)) * 100) if required else 0
    if selection.preparation_supported and not selection.missing_information and not selection.unsupported_conditions and not missing:
        status = "ready"
    elif selection.recommended_itr:
        status = "needs_review"
    else:
        status = "incomplete"

    evidence_items = [item for item in items if item.section == "Documents"]
    return {
        "assessment_year": profile.assessment_year,
        "recommended_itr": selection.recommended_itr,
        "preparation_supported": selection.preparation_supported,
        "status": status,
        "completion_percentage": percentage,
        "complete_count": len(complete),
        "required_count": len(required),
        "missing_count": len(missing),
        "missing": [
            {"key": item.key, "section": item.section, "label": item.label, "reason": item.reason}
            for item in missing
        ],
        "evidence": [
            {"key": item.key, "label": item.label, "available": item.complete, "reason": item.reason}
            for item in evidence_items
        ],
        "selection_reasons": selection.reasons,
        "unsupported_conditions": selection.unsupported_conditions,
        "selection_missing_information": selection.missing_information,
    }
