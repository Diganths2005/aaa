from decimal import Decimal

OLD_REGIME_SLABS = {
    "individual": ((Decimal("250000"), Decimal("0")), (Decimal("500000"), Decimal("0.05")), (Decimal("1000000"), Decimal("0.20")), (None, Decimal("0.30"))),
    "senior": ((Decimal("300000"), Decimal("0")), (Decimal("500000"), Decimal("0.05")), (Decimal("1000000"), Decimal("0.20")), (None, Decimal("0.30"))),
}
NEW_REGIME_SLABS = ((Decimal("400000"), Decimal("0")), (Decimal("800000"), Decimal("0.05")), (Decimal("1200000"), Decimal("0.10")), (Decimal("1600000"), Decimal("0.15")), (Decimal("2000000"), Decimal("0.20")), (Decimal("2400000"), Decimal("0.25")), (None, Decimal("0.30")))
