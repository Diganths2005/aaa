from decimal import Decimal

SECTION_111A_RATE = Decimal("0.20")
SECTION_112_RATE = Decimal("0.125")
SECTION_112A_RATE = Decimal("0.125")
SECTION_112A_EXEMPTION = Decimal("125000")
CAPITAL_GAIN_ASSET_TYPES = {
    "listed_equity_share",
    "equity_oriented_mutual_fund",
    "other_security",
    "immovable_property",
    "gold_or_other",
}

# FY 2025-26 / AY 2026-27.  Listed financial assets have a 12-month test;
# all other supported assets use the 24-month test.
HOLDING_PERIOD_MONTHS = {
    "listed_equity_share": 12,
    "equity_oriented_mutual_fund": 12,
    "other_security": None,  # 12 months when listed, otherwise 24 months
    "immovable_property": 24,
    "gold_or_other": 24,
}
