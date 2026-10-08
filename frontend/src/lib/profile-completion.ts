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
  const has = (key: keyof TaxProfile) => Array.isArray(profile?.[key]) && (profile?.[key] as unknown[]).length > 0;
  const checks = [
    {
      complete: Boolean(profile?.date_of_birth?.trim() && profile?.pan_number?.trim() && profile?.residential_status),
      missing: 'Personal information',
    },
    {
      complete: Boolean(profile?.employment_type && (profile.employment_type === 'none' || profile.employer_name?.trim() || has('salary_income') || has('business_income'))),
      missing: 'Employment information',
    },
    {
      complete: has('salary_income') || has('pension_income'),
      missing: 'Salary or pension information',
    },
    { complete: has('house_properties'), missing: 'House property information' },
    { complete: has('other_income'), missing: 'Other income information' },
    { complete: has('capital_gains'), missing: 'Capital gains information' },
    { complete: has('deductions') || has('investments'), missing: 'Deduction information' },
    { complete: has('taxes_paid'), missing: 'TDS or tax payment information' },
    { complete: has('bank_accounts'), missing: 'Bank information' },
    { complete: documentCount > 0 || has('documents'), missing: 'Tax documents' },
    {
      complete: [profile?.is_senior_citizen, profile?.is_director, profile?.has_unlisted_equity, profile?.has_foreign_assets, profile?.has_foreign_income, profile?.has_business_income, profile?.has_speculative_income, profile?.has_carry_forward_loss].every((value) => value !== undefined),
      missing: 'Return eligibility details',
    },
  ];
  const completeCount = checks.filter((item) => item.complete).length;
  const hasIncome = ['salary_income', 'pension_income', 'house_properties', 'other_income', 'capital_gains', 'business_income']
    .some((key) => has(key as keyof TaxProfile));

  return {
    percent: Math.round((completeCount / checks.length) * 100),
    missing: checks.filter((item) => !item.complete).map((item) => item.missing),
    minimumReady: Boolean(profile?.date_of_birth?.trim() && profile?.pan_number?.trim() && profile?.residential_status && profile?.employment_type && hasIncome),
  };
};
