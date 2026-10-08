import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { taxAPI, taxProfileAPI } from '@/lib/api';
import { getProfileCompletion } from '@/lib/profile-completion';
import { useAuthStore } from '@/store/auth';

type Comparison = {
  recommended_regime: string;
  estimated_saving: number;
  old_regime: Record<string, number>;
  new_regime: Record<string, number>;
};

const money = (value: number | string | undefined) => value === undefined || value === null
  ? '—'
  : `₹${Number(value).toLocaleString('en-IN')}`;

const TaxCalculationPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authReady, setAuthReady] = useState(false);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [needsProfile, setNeedsProfile] = useState(false);

  useEffect(() => {
    hydrate();
    setAuthReady(true);
  }, [hydrate]);

  useEffect(() => {
    if (!authReady) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    let active = true;
    const load = async () => {
      try {
        const profileResponse = await taxProfileAPI.getCurrentUser();
        if (!getProfileCompletion(profileResponse.data).minimumReady) {
          if (active) setNeedsProfile(true);
          return;
        }
        const result = await taxAPI.compareRegimes(profileResponse.data, true);
        if (active) setComparison(result.data);
      } catch (loadError: any) {
        if (active) setError(loadError?.response?.data?.detail || 'TaxWise could not calculate your tax right now.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [authReady, isAuthenticated, router]);

  if (!authReady || !isAuthenticated || loading) return <main className="min-h-screen bg-[#F8FAFC] p-8 text-[#475569]">Loading TaxWise calculation…</main>;

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Tax calculation</p><h1 className="mt-2 text-3xl font-bold">Your tax summary</h1></div>
          <div className="flex gap-2"><Link href="/dashboard" className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold">← Back</Link><Link href="/dashboard" className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Dashboard</Link></div>
        </header>
        {needsProfile ? (
          <section className="card p-7"><h2 className="text-xl font-bold">Complete your profile to calculate tax</h2><p className="mt-2 text-sm text-[#64748B]">Personal identity details and at least one income source are required. No tax values have been estimated from blank fields.</p><Link href="/tax-profile" className="mt-5 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Complete Profile</Link></section>
        ) : error ? (
          <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{error}</p>
        ) : comparison ? (
          <>
            <section className="mb-5 rounded-3xl border border-[#A7F3D0] bg-white p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#047857]">TaxWise Engine</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl bg-[#F8FAFC] p-4"><p className="text-sm text-[#64748B]">Old regime taxable income</p><p className="mt-2 text-2xl font-bold">{money(comparison.old_regime.taxable_income)}</p></div>
                <div className="rounded-2xl bg-[#F8FAFC] p-4"><p className="text-sm text-[#64748B]">New regime taxable income</p><p className="mt-2 text-2xl font-bold">{money(comparison.new_regime.taxable_income)}</p></div>
              </div>
            </section>
            <section className="grid gap-4 md:grid-cols-2">
              {(['old_regime', 'new_regime'] as const).map((key) => {
                const title = key === 'old_regime' ? 'Old Regime' : 'New Regime';
                const result = comparison[key];
                return (
                  <article key={key} className={`card p-6 ${comparison.recommended_regime === key.split('_')[0] ? 'border-[#10B981]' : ''}`}>
                    <div className="flex items-center justify-between"><h2 className="text-xl font-bold">{title}</h2>{comparison.recommended_regime === key.split('_')[0] && <span className="chip">Recommended</span>}</div>
                    <dl className="mt-5 space-y-3 text-sm">
                      <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Gross total income</dt><dd className="font-semibold">{money(result.gross_total_income)}</dd></div>
                      <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Deductions</dt><dd className="font-semibold">{money(result.total_deductions)}</dd></div>
                      <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Taxable income</dt><dd className="font-semibold">{money(result.taxable_income)}</dd></div>
                      <div className="flex justify-between gap-4 border-t border-[#E2E8F0] pt-3"><dt className="font-semibold">Total tax</dt><dd className="text-lg font-bold">{money(result.total_tax_liability)}</dd></div>
                      <div className="flex justify-between gap-4"><dt className="text-[#64748B]">TDS / taxes paid</dt><dd className="font-semibold">{money(result.total_tax_paid)}</dd></div>
                      {Number(result.refund || 0) > 0
                        ? <div className="rounded-lg bg-[#ECFDF5] p-3"><dt className="text-xs text-[#065F46]">Estimated refund</dt><dd className="mt-1 font-bold text-[#065F46]">{money(result.refund)}</dd><p className="mt-1 text-xs text-[#065F46]">Estimated refund — actual refund is determined by the tax authority.</p></div>
                        : <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Balance payable</dt><dd className="font-semibold">{money(result.balance_payable)}</dd></div>}
                    </dl>
                  </article>
                );
              })}
            </section>
            <p className="mt-5 text-sm text-[#475569]">Recommended regime: <strong className="capitalize">{comparison.recommended_regime}</strong> · Estimated saving: <strong>{money(comparison.estimated_saving)}</strong></p>
            <p className="mt-2 text-xs text-[#64748B]">🧮 Values shown are returned by the TaxWise Engine. They are estimates for review and do not represent a filed return or completed payment.</p>
            <Link href="/itr-selection" className="mt-5 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Continue to ITR preparation</Link>
          </>
        ) : <p className="card p-6">No calculation is available yet.</p>}
      </div>
    </main>
  );
};

export default TaxCalculationPage;
