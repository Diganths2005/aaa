import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { taxAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

type RegimeMetrics = {
  taxable_income: number;
  total_deductions: number;
  total_tax_liability: number;
  cess: number;
  rebate: number;
};

type RegimeComparison = {
  recommended_regime: 'old' | 'new' | 'equal';
  estimated_saving: number;
  old_regime: { taxable_income: number; total_deductions: number; total_tax_liability: number; cess: number; rebate: number };
  new_regime: { taxable_income: number; total_deductions: number; total_tax_liability: number; cess: number; rebate: number };
};

const formatMoney = (value: number) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const CompareRegimesPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [comparison, setComparison] = useState<RegimeComparison | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const profileResponse = await taxProfileAPI.getCurrentUser();
        const result = await taxAPI.compareRegimes(profileResponse.data);
        setComparison({
          recommended_regime: result.data.recommended_regime,
          estimated_saving: Number(result.data.estimated_saving || 0),
          old_regime: {
            taxable_income: Number(result.data.old_regime.taxable_income || 0),
            total_deductions: Number(result.data.old_regime.total_deductions || 0),
            total_tax_liability: Number(result.data.old_regime.total_tax_liability || 0),
            cess: Number(result.data.old_regime.cess || 0),
            rebate: Number(result.data.old_regime.rebate || 0),
          },
          new_regime: {
            taxable_income: Number(result.data.new_regime.taxable_income || 0),
            total_deductions: Number(result.data.new_regime.total_deductions || 0),
            total_tax_liability: Number(result.data.new_regime.total_tax_liability || 0),
            cess: Number(result.data.new_regime.cess || 0),
            rebate: Number(result.data.new_regime.rebate || 0),
          },
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
    { icon: '🤖', label: 'Explained by TaxWise AI' },
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
          <Link href="/taxwise" className="rounded-xl border border-border bg-white px-4 py-2 text-sm font-semibold text-[#0F172A] hover:bg-[#F8FAFC]">Ask TaxWise why</Link>
        </header>

        {loading ? (
          <div className="card p-8 text-sm text-[#64748B]">Loading your current tax comparison…</div>
        ) : error ? (
          <div className="card border-red-200 bg-red-50 p-8 text-red-700">{error}</div>
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
                      ['Taxable Income', regime.taxable_income],
                      ['Deductions', regime.total_deductions],
                      ['Tax', regime.total_tax_liability],
                      ['Cess', regime.cess],
                      ['Final Tax', regime.total_tax_liability],
                    ].map(([name, value]) => (
                      <div key={name as string} className="flex items-center justify-between rounded-2xl border border-border bg-white px-4 py-3">
                        <span className="text-sm text-[#64748B]">{name as string}</span>
                        <span className="text-base font-semibold text-[#0F172A]">{formatMoney(Number(value || 0))}</span>
                      </div>
                    ))}
                  </div>
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
                <p className="mt-2 text-base font-semibold text-[#0F172A]">Deterministic Tax Engine</p>
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
