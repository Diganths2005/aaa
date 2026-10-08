import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { taxAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';
import { getProfileCompletion } from '@/lib/profile-completion';

type RegimeMetrics = {
  gross_total_income: number;
  ordinary_taxable_income: number;
  taxable_income: number;
  total_deductions: number;
  tax_before_rebate: number;
  tax_after_rebate: number;
  total_tax_liability: number;
  cess: number;
  rebate: number;
  surcharge: number;
  capital_gains_tax: number;
  total_tax_paid: number;
  refund: number;
  balance_payable: number;
  slab_calculation: Array<{ lower_bound: number; upper_bound: number | null; rate: number; taxable_amount: number; tax: number }>;
};

type RegimeComparison = {
  recommended_regime: 'old' | 'new' | 'equal';
  estimated_saving: number;
  old_regime: RegimeMetrics;
  new_regime: RegimeMetrics;
};

const formatMoney = (value: number) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const CompareRegimesPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState<RegimeComparison | null>(null);
  const [error, setError] = useState('');
  const [needsProfile, setNeedsProfile] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const profileResponse = await taxProfileAPI.getCurrentUser();
        if (!getProfileCompletion(profileResponse.data).minimumReady) {
          setNeedsProfile(true);
          return;
        }
        const result = await taxAPI.compareRegimes(profileResponse.data, true);
        const summarize = (taxResult: any): RegimeMetrics => ({
          gross_total_income: Number(taxResult.gross_total_income || 0),
          ordinary_taxable_income: Number(taxResult.ordinary_taxable_income || 0),
          taxable_income: Number(taxResult.taxable_income || 0),
          total_deductions: Number(taxResult.total_deductions || 0),
          tax_before_rebate: Number(taxResult.tax_before_rebate || 0),
          tax_after_rebate: Number(taxResult.tax_after_rebate || 0),
          total_tax_liability: Number(taxResult.total_tax_liability || 0),
          cess: Number(taxResult.cess || 0),
          rebate: Number(taxResult.rebate || 0),
          surcharge: Number(taxResult.surcharge || 0),
          capital_gains_tax: Number(taxResult.capital_gains_tax || 0),
          total_tax_paid: Number(taxResult.total_tax_paid || 0),
          refund: Number(taxResult.refund || 0),
          balance_payable: Number(taxResult.balance_payable || 0),
          slab_calculation: (taxResult.slab_calculation || []).map((step: any) => ({
            lower_bound: Number(step.lower_bound || 0),
            upper_bound: step.upper_bound === null ? null : Number(step.upper_bound),
            rate: Number(step.rate || 0),
            taxable_amount: Number(step.taxable_amount || 0),
            tax: Number(step.tax || 0),
          })),
        });
        setComparison({
          recommended_regime: result.data.recommended_regime,
          estimated_saving: Number(result.data.estimated_saving || 0),
          old_regime: summarize(result.data.old_regime),
          new_regime: summarize(result.data.new_regime),
        });
      } catch (err: any) {
        setError(err.response?.data?.detail || 'TaxWise needs a complete tax profile before comparing regimes.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAuthenticated, router]);

  const recommendationText = useMemo(() => {
    if (!comparison) {
      return 'TaxWise is preparing your regime comparison.';
    }
    if (comparison.recommended_regime === 'old') {
      return `Based on your confirmed information, the Old Regime currently results in ₹${comparison.estimated_saving.toLocaleString('en-IN')} less tax.`;
    }
    if (comparison.recommended_regime === 'new') {
      return `Based on your confirmed information, the New Regime currently results in ₹${comparison.estimated_saving.toLocaleString('en-IN')} less tax.`;
    }
    return 'Based on your confirmed information, both regimes are effectively equal.';
  }, [comparison]);

  const sourceBadges = [
    { icon: '🧮', label: 'Calculated by TaxWise Engine' },
    { icon: '✓', label: 'Breakdown from engine results' },
  ];

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Compare Regimes</p>
            <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Old vs New regime</h1>
          </div>
          <div className="flex flex-wrap gap-3">
            <ReturnToDashboard />
            <Link href="/taxwise" className="rounded-xl border border-border bg-white px-4 py-2 text-sm font-semibold text-[#0F172A] hover:bg-[#F8FAFC]">Ask TaxWise why</Link>
          </div>
        </header>

        {loading ? (
          <div className="card p-8 text-sm text-[#64748B]">Loading your current tax comparison…</div>
        ) : error ? (
          <div className="card border-red-200 bg-red-50 p-8 text-red-700">{error}</div>
        ) : needsProfile ? (
          <div className="card p-8"><p className="font-semibold">Complete the minimum Tax Profile information before comparing regimes.</p><Link href="/tax-profile" className="mt-4 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Complete Profile</Link></div>
        ) : comparison ? (
          <>
            <div className="card mb-8 p-6">
              <div className="mb-4 flex flex-wrap gap-2">
                {sourceBadges.map((badge) => (
                  <span key={badge.label} className="chip text-[11px] font-semibold tracking-wide">
                    <span className="mr-1">{badge.icon}</span>
                    {badge.label}
                  </span>
                ))}
              </div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TaxWise recommendation</p>
              <h2 className="mt-3 text-2xl font-bold text-[#0F172A]">{recommendationText}</h2>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              {[
                { label: 'Old Regime', regime: comparison.old_regime, accent: 'bg-[#F8FAFC]' },
                { label: 'New Regime', regime: comparison.new_regime, accent: 'bg-[#ECFDF5]' },
              ].map(({ label, regime, accent }) => (
                <div key={label} className={`card p-6 ${accent}`}>
                  <div className="mb-5 flex items-center justify-between">
                    <h3 className="text-2xl font-bold text-[#0F172A]">{label}</h3>
                    {label === 'Old Regime' && comparison.recommended_regime === 'old' ? (
                      <span className="chip">Recommended</span>
                    ) : label === 'New Regime' && comparison.recommended_regime === 'new' ? (
                      <span className="chip">Recommended</span>
                    ) : null}
                  </div>

                  <div className="space-y-3">
                    {[
                      ['Gross Total Income', regime.gross_total_income],
                      ['Taxable Income', regime.taxable_income],
                      ['Deductions', regime.total_deductions],
                      ['Final Tax', regime.total_tax_liability],
                    ].map(([name, value]) => (
                      <div key={name as string} className="flex items-center justify-between rounded-2xl border border-border bg-white px-4 py-3">
                        <span className="text-sm text-[#64748B]">{name as string}</span>
                        <span className="text-base font-semibold text-[#0F172A]">{formatMoney(Number(value || 0))}</span>
                      </div>
                    ))}
                  </div>
                  <details className="mt-5 border-t border-border pt-4">
                    <summary className="cursor-pointer text-sm font-semibold text-[#047857]">Why this result?</summary>
                    <div className="mt-4 space-y-2 text-sm">
                      <p>Ordinary taxable income through slabs: {formatMoney(regime.ordinary_taxable_income)}</p>
                      {regime.slab_calculation.map((step, index) => (
                        <p key={`${step.lower_bound}-${index}`} className="text-[#475569]">
                          {step.upper_bound === null ? `Above ${formatMoney(step.lower_bound)}` : `${formatMoney(step.lower_bound)} to ${formatMoney(step.upper_bound)}`}: {formatMoney(step.taxable_amount)} at {step.rate * 100}% = {formatMoney(step.tax)}
                        </p>
                      ))}
                      <p>Special-rate capital-gain tax: {formatMoney(regime.capital_gains_tax)}</p>
                      <p>Tax before rebate: {formatMoney(regime.tax_before_rebate)}</p>
                      <p>Rebate: {formatMoney(regime.rebate)}</p>
                      <p>Tax after rebate: {formatMoney(regime.tax_after_rebate)}</p>
                      <p>Surcharge: {formatMoney(regime.surcharge)}</p>
                      <p>Cess: {formatMoney(regime.cess)}</p>
                      <p>Taxes already paid: {formatMoney(regime.total_tax_paid)}</p>
                      <p>Refund: {formatMoney(regime.refund)} · Payable: {formatMoney(regime.balance_payable)}</p>
                    </div>
                  </details>
                </div>
              ))}
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <div className="card p-5">
                <p className="text-sm text-[#64748B]">Difference</p>
                <p className="mt-2 text-2xl font-bold text-[#0F172A]">{formatMoney(Math.abs(comparison.estimated_saving))}</p>
              </div>
              <div className="card p-5">
                <p className="text-sm text-[#64748B]">Tax source</p>
                <p className="mt-2 text-base font-semibold text-[#0F172A]">Based on your confirmed numbers</p>
              </div>
              <div className="card p-5">
                <p className="text-sm text-[#64748B]">Status</p>
                <p className="mt-2 text-base font-semibold text-[#047857]">{comparison.recommended_regime === 'equal' ? 'Equivalent' : 'Recommendation available'}</p>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
};

export default CompareRegimesPage;
