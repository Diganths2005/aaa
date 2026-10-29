from io import BytesIO
from typing import Any
import json
import re

from openpyxl import load_workbook

from .complete_field_extractor import extract_complete_candidates
from .field_extractor import extract_candidates, normalize_date_of_birth, parse_currency
from .models import ExtractedCandidate, ExtractionResult

PROFILE_IMPORT_SHEET = "TaxWise Profile Import"

IMPORT_FIELDS = {
    "employee name": ("name", "text"), "taxpayer name": ("name", "text"), "name": ("name", "text"),
    "pan": ("pan_number", "pan"), "pan number": ("pan_number", "pan"),
    "date of birth": ("date_of_birth", "date"), "dob": ("date_of_birth", "date"),
    "employer": ("employer_name", "text"), "employer name": ("employer_name", "text"),
    "gross salary": ("salary_income", "currency"), "salary": ("salary_income", "currency"),
    "tds deducted": ("tds", "currency"), "tds": ("tds", "currency"),
    "professional tax": ("professional_tax", "currency"), "standard deduction": ("standard_deduction", "currency"),
    "pension income": ("pension_income", "currency"), "family pension": ("other_income_family_pension", "currency"),
    "annual rent": ("house_property_rent", "currency"), "rent received": ("house_property_rent", "currency"),
    "municipal tax": ("house_property_municipal_tax", "currency"),
    "home loan interest": ("house_property_loan_interest", "currency"),
    "interest on home loan": ("house_property_loan_interest", "currency"),
    "professional receipts": ("business_receipts", "currency"),
    "professional expenses": ("business_expenses", "currency"),
    "net professional income": ("business_net_income", "currency"),
    "bank interest": ("other_income_interest", "currency"), "interest income": ("other_income_interest", "currency"),
    "dividend income": ("other_income_dividend", "currency"), "dividend": ("other_income_dividend", "currency"),
    "advance tax": ("advance_tax", "currency"), "self assessment tax": ("self_assessment_tax", "currency"),
    "section 80c": ("deduction_80C", "currency"), "80c": ("deduction_80C", "currency"),
    "section 80d": ("deduction_80D", "currency"), "80d": ("deduction_80D", "currency"),
    "80ccd(1b)": ("deduction_80CCD_1B", "currency"), "80g": ("deduction_80G", "currency"),
    "80e": ("deduction_80E", "currency"), "80ee": ("deduction_80EE", "currency"),
    "80eea": ("deduction_80EEA", "currency"), "80gg": ("deduction_80GG", "currency"),
    "80u": ("deduction_80U", "currency"), "80dd": ("deduction_80DD", "currency"),
    "80ddb": ("deduction_80DDB", "currency"),
}

def _cell_text(value: Any) -> str:
    if value is None: return ""
    if isinstance(value, float) and value.is_integer(): return str(int(value))
    return str(value).strip()

def _workbook_rows(content: bytes) -> list[tuple[str,int,list[str]]]:
    try:
        wb=load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise ValueError("INVALID_SPREADSHEET") from exc
    rows=[]
    for ws in wb.worksheets:
        for i,row in enumerate(ws.iter_rows(values_only=True),1):
            vals=[_cell_text(v) for v in row]
            if any(vals): rows.append((ws.title,i,vals))
    wb.close()
    if not rows: raise ValueError("EMPTY_SPREADSHEET")
    return rows

def _profile_import(rows: list[tuple[str,int,list[str]]]) -> list[ExtractedCandidate]:
    sheet_rows=[r for r in rows if r[0]==PROFILE_IMPORT_SHEET]
    if not sheet_rows: return []
    values={}
    for _,_,cells in sheet_rows:
        if len(cells)<2: continue
        key=cells[0].strip().lower()
        value=cells[1].strip()
        if key in {"profile field","your value","guidance","instructions","title"} or not value: continue
        if key in values: raise ValueError("DUPLICATE_IMPORT_FIELD")
        values[key]=value
    if not values: return []
    mapped={}
    for key,value in values.items():
        if key in {"taxpayer_name"}: field="name"; kind="text"
        elif key in {"pan_number"}: field="pan_number"; kind="pan"
        elif key in {"residential_status","employment_type","has_business_income"}: mapped[key]=value.lower() in {"yes","true","1"} if key=="has_business_income" else value; continue
        else:
            if key not in IMPORT_FIELDS: raise ValueError("UNKNOWN_PROFILE_IMPORT_FIELD")
            field,kind=IMPORT_FIELDS[key]
        if kind=="currency": parsed=parse_currency(value)
        elif kind=="date": parsed=normalize_date_of_birth(value)
        elif kind=="pan":
            if not re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]",value.upper()): raise ValueError("INVALID_IMPORT_PAN")
            parsed=value.upper()
        else: parsed=value
        mapped[field]=str(parsed) if hasattr(parsed,"as_tuple") else parsed
    return [ExtractedCandidate("profile_import",json.dumps(mapped,default=str),"PROFILE_IMPORT","high",1)]

def process_spreadsheet(content: bytes) -> ExtractionResult:
    rows=_workbook_rows(content)
    imported=_profile_import(rows)
    if imported:
        return ExtractionResult("\n".join(" | ".join(r[2]) for r in rows),len({r[0] for r in rows}),imported,"spreadsheet")
    pages=[]
    for sheet,row,cells in rows:
        pages.append(f"Sheet: {sheet} Row {row}: " + " | ".join(cells))
    text="\n".join(pages)
    candidates=extract_complete_candidates([text],"SPREADSHEET")
    seen={c.field for c in candidates}
    candidates.extend(c for c in extract_candidates([text],"SPREADSHEET") if c.field not in seen)
    return ExtractionResult(text,len({r[0] for r in rows}),candidates,"spreadsheet")
