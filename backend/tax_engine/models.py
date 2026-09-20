from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from schemas.tax_profile import TaxProfileCreate

Regime = Literal["old", "new"]
RecommendedRegime = Literal["old", "new", "equal"]


class TaxCalculationInput(BaseModel):
    profile: TaxProfileCreate
    regime: Regime


class CapitalGainResult(BaseModel):
    asset_type: str
    holding_period: Literal["short_term", "long_term"]
    sale_consideration: Decimal
    acquisition_cost: Decimal
    improvement_cost: Decimal
    transfer_expenses: Decimal
    computed_gain: Decimal
    gain_type: Literal["gain", "loss"]
    applicable_section: Literal["111A", "112", "112A", "slab"]
    special_rate: Optional[Decimal] = None
    taxable_gain: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    loss_setoff: Decimal = Field(ge=0)
    carry_forward: Decimal = Field(ge=0)


class CapitalGainsSummary(BaseModel):
    transactions: list[CapitalGainResult] = Field(default_factory=list)
    short_term_capital_gain: Decimal = Field(ge=0)
    long_term_capital_gain: Decimal = Field(ge=0)
    short_term_capital_loss: Decimal = Field(ge=0)
    long_term_capital_loss: Decimal = Field(ge=0)
    current_year_capital_gain_after_setoff: Decimal = Field(ge=0)
    capital_loss_carry_forward: Decimal = Field(ge=0)
    ordinary_short_term_capital_gain: Decimal = Field(ge=0)
    special_rate_capital_gain: Decimal = Field(ge=0)
    special_rate_tax: Decimal = Field(ge=0)
    itr1_capital_gain_eligible: bool
    itr1_capital_gain_reason: str


class TaxCalculationResult(BaseModel):
    income_from_salary: Decimal
    income_from_pension: Decimal
    house_property_income: Decimal
    house_property_loss: Decimal
    house_property_loss_set_off: Decimal
    house_property_loss_carried_forward: Decimal
    other_sources_income: Decimal
    business_income: Decimal
    capital_gains: CapitalGainsSummary
    ordinary_taxable_income: Decimal
    capital_gains_tax: Decimal
    assessment_year: str
    gross_total_income: Decimal
    total_deductions: Decimal
    taxable_income: Decimal
    tax_before_rebate: Decimal
    rebate: Decimal
    surcharge: Decimal
    cess: Decimal
    total_tax_liability: Decimal
    tds: Decimal
    advance_tax: Decimal
    self_assessment_tax: Decimal
    total_tax_paid: Decimal
    balance_payable: Decimal
    refund: Decimal
    regime: Regime

    @field_validator("gross_total_income", "total_deductions", "taxable_income", "tax_before_rebate", "rebate", "surcharge", "cess", "total_tax_liability", "tds", "advance_tax", "self_assessment_tax", "total_tax_paid", "balance_payable", "refund")
    @classmethod
    def non_negative_result(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Calculated result cannot be negative")
        return value


class RegimeComparison(BaseModel):
    old_regime: TaxCalculationResult
    new_regime: TaxCalculationResult
    recommended_regime: RecommendedRegime
    estimated_saving: Decimal = Field(ge=0)


class TaxEngineError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)
