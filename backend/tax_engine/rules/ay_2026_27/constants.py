from decimal import Decimal

CESS_RATE = Decimal("0.04")
NEW_REGIME_REBATE_LIMIT = Decimal("1200000")
NEW_REGIME_REBATE_MAX = Decimal("60000")
OLD_REGIME_REBATE_LIMIT = Decimal("500000")
OLD_REGIME_REBATE_MAX = Decimal("12500")
SURCHARGE_THRESHOLDS = ((Decimal("5000000"), Decimal("0.10")), (Decimal("10000000"), Decimal("0.15")), (Decimal("20000000"), Decimal("0.25")), (Decimal("50000000"), Decimal("0.37")))
