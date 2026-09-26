import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { deductionsAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';

type DeductionRecord = {
  section: string;
  name: string;
  claimedAmount: number;
  eligibleAmount: number;
  appliedAmount: number;
  regime: 'old' | 'new';
  status: string;
  reasonCode: string;
  explanation: string;
  requiredInformation: string[];
  requiredDocuments: string[];
  source: string;
  confirmed: boolean;
  lastUpdated: string;
};

const money = (value: number) => `₹${(value || 0).toLocaleString('en-IN')}`;

const statusTone: Record<string, string> = {
  UNKNOWN: 'bg-amber-50 text-amber-700 border-amber-200',
  NEEDS_INFORMATION: 'bg-amber-50 text-amber-700 border-amber-200',
  POTENTIALLY_ELIGIBLE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  ELIGIBLE: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  NOT_ELIGIBLE: 'bg-red-50 text-red-700 border-red-200',
  CONFIRMED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  APPLIED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  NOT_APPLICABLE: 'bg-slate-100 text-slate-700 border-slate-200',
};

const DeductionsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [records, setRecords] = useState<DeductionRecord[]>([]);
  const [summary, setSummary] = useState<{ potentialDeductions: number; confirmedDeductions: number; appliedDeductions: number; potentialTaxImpact: number; discoveryCount: number } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const load = async () => {
      try {
        const profileResponse = await taxProfileAPI.getCurrentUser();
        if (!profileResponse.data) {
          setError('Complete your tax profile to unlock deduction discovery.');
          return;
        }
        const [discoveryResponse, summaryResponse] = await Promise.all([
          deductionsAPI.discover('old'),
          deductionsAPI.summary('old'),
        ]);
        setRecords(discoveryResponse.data || []);
        setSummary(summaryResponse.data || null);
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Could not load deduction opportunities.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Deduction discovery</p>
            <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Potential tax savings</h1>
          </div>
          <ReturnToDashboard />
        </header>

        {loading ? (
          <div className="card p-8 text-sm text-[#64748B]">Reviewing your deduction profile…</div>
        ) : (
          <>
            {error ? (
              <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
            ) : null}

            {summary && (
              <div className="mb-8 grid gap-4 md:grid-cols-4">
                <div className="card p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#64748B]">Potential deductions</p>
                  <p className="mt-3 text-2xl font-bold text-[#0F172A]">{money(summary.potentialDeductions)}</p>
                </div>
                <div className="card p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#64748B]">Confirmed deductions</p>
                  <p className="mt-3 text-2xl font-bold text-[#0F172A]">{money(summary.confirmedDeductions)}</p>
                </div>
                <div className="card p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#64748B]">Applied deductions</p>
                  <p className="mt-3 text-2xl font-bold text-[#0F172A]">{money(summary.appliedDeductions)}</p>
                </div>
                <div className="card p-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#64748B]">Potential tax impact</p>
                  <p className="mt-3 text-2xl font-bold text-[#0F172A]">{money(summary.potentialTaxImpact)}</p>
                </div>
              </div>
            )}

            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {records.map((item) => (
                <div key={item.section} className="card p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xl font-bold text-[#0F172A]">{item.name}</p>
                      <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#64748B]">{item.section}</p>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${statusTone[item.status] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                      {item.status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="mt-4 space-y-2 text-sm text-[#475569]">
                    <div className="flex justify-between"><span>Claimed</span><strong className="text-[#0F172A]">{money(item.claimedAmount)}</strong></div>
                    <div className="flex justify-between"><span>Eligible</span><strong className="text-[#0F172A]">{money(item.eligibleAmount)}</strong></div>
                    <div className="flex justify-between"><span>Applied</span><strong className="text-[#0F172A]">{money(item.appliedAmount)}</strong></div>
                  </div>

                  <p className="mt-4 text-sm text-[#1E293B]">{item.explanation}</p>

                  {item.requiredInformation.length > 0 && (
                    <div className="mt-4 rounded-xl bg-[#F8FAFC] p-3 text-xs text-[#475569]">
                      <p className="font-semibold text-[#0F172A]">Needed information</p>
                      <ul className="mt-2 list-disc space-y-1 pl-4">
                        {item.requiredInformation.map((field) => <li key={field}>{field}</li>)}
                      </ul>
                    </div>
                  )}

                  {item.requiredDocuments.length > 0 && (
                    <div className="mt-3 rounded-xl bg-[#ECFDF5] p-3 text-xs text-[#047857]">
                      <p className="font-semibold">Documents</p>
                      <ul className="mt-2 list-disc space-y-1 pl-4">
                        {item.requiredDocuments.map((doc) => <li key={doc}>{doc}</li>)}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default DeductionsPage;
