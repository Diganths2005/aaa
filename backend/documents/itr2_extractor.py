from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Iterable

from .field_extractor import parse_currency
from .models import ExtractedCandidate


def _page_for(text: str, start: int) -> int:
    return text[:start].count("\f") + 1


def _first(patterns: Iterable[str], text: str):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match, _page_for(text, match.start())
    return None, None


def _money(value: str) -> Decimal:
    return parse_currency(value)


def _date(value: str) -> str:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return value.strip()


def _transaction_blocks(text: str) -> list[tuple[str, int]]:
    pattern = r"(?:Transaction\s+(?:No\.?\s*)?(\d+)|Capital\s+Gain(?:s)?\s*[-:]\s*([^\n]+))"
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    blocks: list[tuple[str, int]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((text[start:end], _page_for(text, start)))
    return blocks


def extract_itr2_candidates(pages: list[str], source: str = "ITR2_DOCUMENT") -> list[ExtractedCandidate]:
    text = "\f".join(pages)
    out: list[ExtractedCandidate] = []

    text_fields = {
        "residential_status": (r"Residential\s+Status\s*[:|]\s*([^\n|]+)",),
        "citizenship": (r"Citizenship\s*[:|]\s*([^\n|]+)",),
        "nationality": (r"Nationality\s*[:|]\s*([^\n|]+)",),
        "bank_name": (r"Bank\s*[:|]\s*([^\n|]+)",),
        "account_number": (r"(?:Account\s+Number|A/c\s+No\.?)\s*[:|]\s*([A-Z0-9-]+)",),
        "ifsc_code": (r"IFSC(?:\s+Code)?\s*[:|]\s*([A-Z0-9]+)",),
        "account_type": (r"Account\s+Type\s*[:|]\s*([^\n|]+)",),
        "refund_account": (r"(?:Primary|Refund)\s*/?\s*Account\s*[:|]\s*(Yes|No)",),
        "foreign_country": (r"(?:Foreign\s+)?Country\s*[:|]\s*([^\n|]+)",),
        "foreign_asset_type": (r"(?:Foreign\s+)?Asset\s+Type\s*[:|]\s*([^\n|]+)",),
        "donation_reference": (r"(?:Donation\s+)?(?:Transaction\s+)?Reference\s*[:|]\s*([^\n|]+)",),
    }
    for field, patterns in text_fields.items():
        match, page = _first(patterns, text)
        if match:
            out.append(ExtractedCandidate(field, match.group(1).strip(), source, "high", page))

    money_fields = {
        "foreign_maximum_balance": (r"Maximum\s+Balance\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
        "foreign_income": (r"Foreign\s+Income(?:\s+Earned)?\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
        "donation_amount": (r"Donation(?:\s+Amount)?\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",),
    }
    for field, patterns in money_fields.items():
        match, page = _first(patterns, text)
        if match:
            try:
                value = _money(match.group(1))
            except ValueError:
                continue
            out.append(ExtractedCandidate(field, value, source, "high", page))

    for index, (block, page) in enumerate(_transaction_blocks(text), start=1):
        def value(patterns):
            match, _ = _first(patterns, block)
            return match.group(1).strip() if match else None

        asset = value((r"(?:Asset|Security|Property)\s*[:|]\s*([^\n|]+)",))
        if asset:
            normalized = asset.lower()
            if "property" in normalized or "land" in normalized or "building" in normalized:
                asset = "immovable_property"
            elif "mutual fund" in normalized and "equity" in normalized:
                asset = "equity_oriented_mutual_fund"
            elif "equity" in normalized or "share" in normalized:
                asset = "listed_equity_share"
            else:
                asset = "other_security"
        purchase = value((r"(?:Purchase|Acquisition)\s+Date\s*[:|]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})",))
        sale_date = value((r"Sale\s+Date\s*[:|]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})",))

        def money(patterns):
            raw = value(patterns)
            if raw is None:
                return None
            try:
                return str(_money(raw))
            except ValueError:
                return None

        transaction = {
            "transaction_number": index,
            "asset_type": asset,
            "acquisition_date": _date(purchase) if purchase else None,
            "sale_date": _date(sale_date) if sale_date else None,
            "sale_consideration": money((r"Sale\s+Consideration\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)", r"Sale\s+Value\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)")),
            "acquisition_cost": money((r"(?:Acquisition|Purchase)\s+Cost\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)", r"Cost\s+of\s+Acquisition\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)")),
            "improvement_cost": money((r"Improvement\s+Cost\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",)),
            "transfer_expenses": money((r"Transfer\s+Expenses?\s*[:|]\s*[^\d\n]*([\d,.]+(?:\s*(?:lakh|lakhs|lac|l))?)",)),
            "stt_paid": value((r"STT(?:\s+Paid(?:\s+on\s+Transfer)?)?\s*[:|]\s*(Yes|No)",)),
        }
        if any(item is not None for key, item in transaction.items() if key != "transaction_number"):
            out.append(ExtractedCandidate(f"capital_gain_transaction_{index}", transaction, source, "high", page))

    return out
