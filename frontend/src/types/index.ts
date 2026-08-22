export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  createdAt: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type Money = number;
export interface SalaryIncome { employer_name: string; gross_salary: Money; standard_deduction: Money; professional_tax: Money; tds: Money; }
export interface PensionIncome { payer_name: string; amount: Money; tds: Money; }
export interface HouseProperty { property_type: 'self_occupied' | 'let_out' | 'deemed_let_out'; city: string; annual_rent: Money; municipal_tax: Money; home_loan_interest: Money; ownership_share: number; loan_purpose?: 'purchase_or_construction' | 'repair'; loan_sanction_date?: string; construction_completed_within_five_years?: boolean; }
export interface OtherIncome { income_type: 'interest' | 'dividend' | 'family_pension' | 'other'; description: string; amount: Money; tds: Money; }
export interface CapitalGain { asset_type: 'equity' | 'mutual_fund' | 'property' | 'other'; holding_period: 'short_term' | 'long_term'; sale_value: Money; cost_of_acquisition: Money; transfer_expenses: Money; gain_or_loss: Money; }
export interface BusinessIncome { business_name: string; nature_of_business: string; gross_receipts: Money; net_profit_or_loss: Money; presumptive_section?: '44AD' | '44ADA' | '44AE'; }
export interface ForeignIncomeAsset { country: string; item_type: 'income' | 'bank_account' | 'security' | 'immovable_property'; description: string; value: Money; }
export interface Investment { investment_type: string; amount: Money; }
export interface Deduction {
  section: string; amount: Money; self_health_insurance?: Money; family_health_insurance?: Money; parents_health_insurance?: Money;
  parents_senior?: boolean; employer_contribution?: Money; employer_is_government?: boolean; basic_salary?: Money;
  dearness_allowance_for_retirement?: Money; donation_category?: '100_no_limit' | '50_no_limit' | '100_qualifying_limit' | '50_qualifying_limit';
  specified_disease?: boolean; reimbursement_amount?: Money; annual_rent?: Money; owns_residential_property?: boolean; has_hra?: boolean;
  education_loan_interest?: Money; education_loan_eligible?: boolean; disability_percentage?: number; is_dependent?: boolean;
  medical_expenditure?: Money; loan_sanction_date?: string; first_home_owner?: boolean; property_stamp_duty_value?: Money; loan_amount?: Money;
  dependent_relationship?: 'spouse' | 'child' | 'parent' | 'sibling'; dependent_age_category?: 'individual' | 'senior' | 'super_senior'; disability_certificate_available?: boolean;
  donation_mode?: 'cash' | 'non_cash'; donation_eligible?: boolean; form_10ba_acknowledgement?: string; owns_residential_property_at_residence_or_work?: boolean;
  loan_from_financial_institution?: boolean; section_24b_limit_exhausted?: boolean;
}
export interface TaxPayment { tax_type: 'tds' | 'advance_tax' | 'self_assessment'; amount: Money; reference?: string; }
export interface BankAccount { bank_name: string; account_number: string; ifsc_code: string; account_type: 'savings' | 'current' | 'nro' | 'nre'; is_primary: boolean; }
export interface DocumentReference { document_type: 'form_16' | 'ais' | 'form_26as' | 'bank_statement' | 'investment' | 'other'; file_name: string; uploaded_at?: string; }

export interface TaxProfile {
  id?: string; user_id?: string; date_of_birth?: string; pan_number?: string; gender?: string; marital_status?: string;
  address?: string; city?: string; state?: string; pincode?: string; citizenship?: string; nationality?: string;
  residential_status: 'resident' | 'non_resident' | 'nri'; employment_type: 'salaried' | 'self_employed' | 'both' | 'none';
  employer_name?: string; employer_address?: string; financial_year: string; assessment_year: string;
  is_senior_citizen: boolean; is_director: boolean; has_unlisted_equity: boolean; has_foreign_assets: boolean;
  has_foreign_income: boolean; has_business_income: boolean; has_speculative_income: boolean; has_carry_forward_loss: boolean;
  salary_income: SalaryIncome[]; pension_income: PensionIncome[]; house_properties: HouseProperty[];
  other_income: OtherIncome[]; capital_gains: CapitalGain[]; business_income: BusinessIncome[];
  foreign_income_assets: ForeignIncomeAsset[]; investments: Investment[]; deductions: Deduction[];
  taxes_paid: TaxPayment[]; bank_accounts: BankAccount[]; documents: DocumentReference[];
}

export interface AuthStore {
  user: User | null; token: string | null; isAuthenticated: boolean; isLoading: boolean; error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, firstName: string, lastName: string, password: string) => Promise<void>;
  logout: () => void;
}
