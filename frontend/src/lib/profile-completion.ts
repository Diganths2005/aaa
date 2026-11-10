import { TaxProfile } from '@/types';

export type ProfileCompletion = {
  percent: number;
  missing: string[];
  minimumReady: boolean;
};

export const getProfileCompletion = (
  profile: Partial<TaxProfile> | null | undefined,
  documentCount = 0,
): ProfileCompletion => {
  if (!profile) {
    return { percent: 0, missing: ['Personal information', 'Income source'], minimumReady: false };
  }

  const has = (key: keyof TaxProfile) =>
    Array.isArray(profile[key]) && (profile[key] as unknown[]).length > 0;

  const checks: { complete: boolean; missing: string }[] = [
    {
      complete: Boolean(profile.date_of_birth?.trim() && profile.pan_number?.trim() && profile.residential_status),
      missing: 'Personal information',
    },
    {
      complete: Boolean(profile.employment_type),
      missing: 'Employment information',
    },
    {
      complete: ['salary_income', 'pension_income', 'house_properties', 'other_income', 'capital_gains', 'business_income']
        .some((key) => has(key as keyof TaxProfile)),
      missing: 'Income source',
    },
  ];

  // Only applicable sections count toward completion. An employee with no
  // capital gains is NOT missing a "capital gains section"; this was the reason
  // the old UI could get stuck around 50–60% even with a perfectly valid ITR-1.
  if (has('salary_income')) {
    checks.push({
      complete: Boolean(
        profile.salary_income?.every(
          (item) => Boolean(item.employer_name?.trim()) && Number(item.gross_salary ?? 0) >= 0,
        ),
      ),
      missing: 'Salary information',
    });
  }

  if (has('pension_income')) {
    checks.push({
      complete: Boolean(
        profile.pension_income?.every(
          (item) => Boolean(item.payer_name?.trim()) && Number(item.amount ?? 0) >= 0,
        ),
      ),
      missing: 'Pension information',
    });
  }

  if (has('house_properties')) {
    checks.push({
      complete: Boolean(
        profile.house_properties?.every(
          (item) =>
            Boolean(item.city?.trim()) &&
            Boolean(item.property_type) &&
            Number(item.ownership_share ?? 0) > 0,
        ),
      ),
      missing: 'House property information',
    });
  }

  if (has('other_income')) {
    checks.push({
      complete: Boolean(
        profile.other_income?.every(
          (item) =>
            Boolean(item.income_type) &&
            Boolean(item.description?.trim()) &&
            Number(item.amount ?? 0) >= 0,
        ),
      ),
      missing: 'Other income information',
    });
  }

  if (has('capital_gains')) {
    checks.push({
      complete: Boolean(
        profile.capital_gains?.every(
          (item) =>
            Boolean(item.acquisition_date) &&
            Boolean(item.sale_date) &&
            item.sale_consideration != null &&
            item.acquisition_cost != null,
        ),
      ),
      missing: 'Capital-gains transaction details',
    });
  }

  if (has('business_income')) {
    checks.push({
      complete: Boolean(
        profile.business_income?.every(
          (item) =>
            Boolean(item.business_name?.trim()) &&
            Boolean(item.nature_of_business?.trim()) &&
            Number(item.gross_receipts ?? 0) >= 0 &&
            item.net_profit_or_loss != null,
        ),
      ),
      missing: 'Business/professional income details',
    });
  }

  if (profile.has_foreign_assets || profile.has_foreign_income || has('foreign_income_assets')) {
    checks.push({
      complete: has('foreign_income_assets'),
      missing: 'Foreign asset/income details',
    });
  }

  if (has('deductions')) {
    checks.push({
      complete: Boolean(profile.deductions?.every((item) => item.section && item.amount != null)),
      missing: 'Deduction details',
    });
  }

  if (has('taxes_paid')) {
    checks.push({
      complete: Boolean(
        profile.taxes_paid?.every((item) => item.tax_type && Number(item.amount ?? 0) >= 0),
      ),
      missing: 'Tax payment details',
    });
  } else if (has('salary_income') || has('pension_income') || has('other_income')) {
    checks.push({
      complete: false,
      missing: 'TDS / tax-payment confirmation',
    });
  }

  // A bank account is required for return preparation/refund handling.
  checks.push({
    complete: has('bank_accounts'),
    missing: 'Bank information',
  });

  // Documents are evidence, not a generic mandatory completion checkbox. A
  // user may legitimately complete a manual return without uploading a file.
  // Their review status is shown separately by the Documents/Reconciliation UI.
  if (documentCount > 0 || has('documents')) {
    checks.push({ complete: true, missing: 'Tax documents' });
  }

  const completeCount = checks.filter((item) => item.complete).length;
  const percent = checks.length ? Math.round((completeCount / checks.length) * 100) : 0;

  const hasIncome = checks[2]?.complete === true;
  const minimumReady = Boolean(
    profile.date_of_birth?.trim() &&
    profile.pan_number?.trim() &&
    profile.residential_status &&
    profile.employment_type &&
    hasIncome &&
    has('bank_accounts'),
  );

  return {
    percent,
    missing: checks.filter((item) => !item.complete).map((item) => item.missing),
    minimumReady,
  };
};
