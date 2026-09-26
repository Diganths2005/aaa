from fastapi import APIRouter, Query

from schemas.tax_profile import TaxProfileCreate
from tax_engine.calculator import calculate_tax, compare_regimes
from tax_engine.models import RegimeComparison, TaxCalculationInput, TaxCalculationResult

router = APIRouter(prefix="/api/tax", tags=["tax-engine"])


@router.post("/calculate", response_model=TaxCalculationResult)
def calculate_tax_endpoint(request: TaxCalculationInput) -> TaxCalculationResult:
    return calculate_tax(request.profile, request.regime)


@router.post("/compare-regimes", response_model=RegimeComparison)
def compare_regimes_endpoint(profile: TaxProfileCreate, allow_expanded_income: bool = Query(default=False)) -> RegimeComparison:
    return compare_regimes(profile, allow_expanded_income=allow_expanded_income)
