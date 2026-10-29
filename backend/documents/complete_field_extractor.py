from decimal import Decimal
import re
from typing import Any

from .field_extractor import first_match, normalize_date_of_birth, parse_currency
from .models import ExtractedCandidate

# Labels intentionally require explicit field names; this avoids turning arbitrary
# nearby numbers into tax values.
TEXT_FIELDS = {
    "name": (r"(?:Employee Name|Taxpayer Name|Name of (?:the )?Employee|Assessee Name)\s*(?:[:|]\s*)?([^\n|]+)",),
    "pan_number": (r"PAN\s*(?:Number|No\.?)?\s*(?:[:|]\s*)?([A-Z]{5}\d{4}[A-Z])",),
    "date_of_birth": (r"(?:Date of Birth|DOB|Birth Date)\s*(?:[:|]\s*)?(\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})",),
    "employer_name": (r"(?:Employer Name|Name and address of the Employer|Employer)\s*(?:[:|]\s*)?([^\n|]+)",),
    "address": (r"(?:Residential Address|Employee Address|Address)\s*(?:[:|]\s*)?([^\n]+)",),
}
MONEY_FIELDS = {
    "salary_income": ("Gross Salary","Gross Pay","Total Gross Salary","Income chargeable under the head Salaries","Total amount of salary received from current employer(s)","Salary as per provisions contained in section 17(1)"),
    "pension_income": ("Pension Income","Family Pension","Income from Pension"),
    "standard_deduction": ("Standard Deduction","Deduction under section 16(ia)"),
    "professional_tax": ("Professional Tax","Tax on Employment"),
    "tds": ("Total amount of TDS deducted","TDS Deducted","Tax Deducted at Source","TDS"),
    "advance_tax": ("Advance Tax",),
    "self_assessment_tax": ("Self-Assessment Tax","Self Assessment Tax"),
    "other_income_interest": ("Bank Interest","Interest Income","Interest from Bank"),
    "other_income_dividend": ("Dividend Income","Dividend"),
    "house_property_rent": ("Annual Rent","Gross Rent","Rent Received","Annual Value","Gross Annual Value"),
    "house_property_municipal_tax": ("Municipal Tax","Municipal Taxes"),
    "house_property_loan_interest": ("Interest on Housing Loan","Interest on Home Loan","Home Loan Interest","Interest payable on borrowed capital","Interest on borrowed capital"),
    "business_receipts": ("Professional Receipts","Gross Receipts","Business Receipts","Turnover"),
    "business_expenses": ("Professional Expenses","Business Expenses"),
    "business_net_income": ("Net Professional Income","Net Business Income","Net Profit"),
    "capital_gains": ("Capital Gains","Net Capital Gain","Capital Gain"),
}
DEDUCTION_LABELS = {
    "80C":"deduction_80C","80D":"deduction_80D","80CCD(1B)":"deduction_80CCD_1B",
    "80G":"deduction_80G","80E":"deduction_80E","80EE":"deduction_80EE","80EEA":"deduction_80EEA",
    "80GG":"deduction_80GG","80U":"deduction_80U","80DD":"deduction_80DD","80DDB":"deduction_80DDB",
}

def _money_pattern(labels: tuple[str,...]) -> str:
    escaped = "|".join(re.escape(x) for x in labels)
    return rf"(?:{escaped})\s*[:|]?\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)"

def extract_complete_candidates(pages: list[str], source: str) -> list[ExtractedCandidate]:
    text="\f".join(pages)
    out=[]
    for field, patterns in TEXT_FIELDS.items():
        found=first_match(text, patterns)
        if found:
            value,page=found
            if field=="date_of_birth": value=normalize_date_of_birth(value)
            out.append(ExtractedCandidate(field,value,source,"high",page))
    for field, labels in MONEY_FIELDS.items():
        found=first_match(text, (_money_pattern(labels),))
        if found:
            raw,page=found
            try: value=parse_currency(raw)
            except ValueError: continue
            out.append(ExtractedCandidate(field,value,source,"high",page))
    for section, field in DEDUCTION_LABELS.items():
        found=first_match(text,(rf"(?:Section\s*)?{re.escape(section)}\s*(?:Investment|Contribution|Deduction)?\s*[:|]?\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",))
        if found:
            raw,page=found
            try: value=parse_currency(raw)
            except ValueError: continue
            out.append(ExtractedCandidate(field,value,source,"high",page))
    return out
