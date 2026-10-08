import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { deductionsAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';
import { getProfileCompletion } from '@/lib/profile-completion';

type Regime = 'old' | 'new';

type DeductionRecord = {
  section: string;
  name: string;
  claimedAmount: number | string;
  eligibleAmount: number | string;
  appliedAmount: number | string;
  regime: Regime;
  status: string;
  reasonCode: string;
  explanation: string;
  requiredInformation: string[];
  requiredDocuments: string[];
  source: string;
  confirmed: boolean;
  lastUpdated: string;
};

type DiscoverySummary = {
  potentialDeductions: number | string;
  confirmedDeductions: number | string;
  appliedDeductions: number | string;
  discoveryCount: number;
  unknownCount: number;
  needsInfoCount: number;
  potentialCount: number;
};

type TaxProfileSummary = {
  assessment_year: string;
  deductions: Array<{ section: string; amount: number | string }>;
};

const amount = (value: number | string | undefined) => Number(value || 0);
const money = (value: number | string | undefined) =>
  `₹${amount(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const statusStyles: Record<string, string> = {
  UNKNOWN: 'border-amber-200 bg-amber-50 text-amber-800',
  NEEDS_INFORMATION: 'border-amber-200 bg-amber-50 text-amber-800',
  POTENTIALLY_ELIGIBLE: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  ELIGIBLE: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  NOT_ELIGIBLE: 'border-red-200 bg-red-50 text-red-700',
  CONFIRMED: 'border-blue-200 bg-blue-50 text-blue-800',
  APPLIED: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  NOT_APPLICABLE: 'border-slate-200 bg-slate-100 text-slate-700',
};

const statusLabel = (status: string) =>
  status.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

const getErrorMessage = (error: unknown) => {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : 'We could not load your deduction review. Please try again.';
};

const DeductionsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authHydrated, setAuthHydrated] = useState(false);
  const [regime, setRegime] = useState<Regime>('old');
  const [records, setRecords] = useState<DeductionRecord[]>([]);
  const [summary, setSummary] = useState<DiscoverySummary | null>(null);
  const [profile, setProfile] = useState<TaxProfileSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [needsProfile, setNeedsProfile] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    hydrate();
    setAuthHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (!authHydrated) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }

    let active = true;
    setLoading(true);
    setError('');
    const load = async () => {
      try {
        const profileResponse = await taxProfileAPI.getCurrentUser();
        if (!active) return;
        setProfile(profileResponse.data);
        if (!getProfileCompletion(profileResponse.data).minimumReady) {
          setNeedsProfile(true);
          setError('Complete the minimum Tax Profile information before viewing personalized deduction opportunities.');
          return;
        }
        setNeedsProfile(false);
        const [discoveryResponse, summaryResponse] = await Promise.all([
          deductionsAPI.discover(regime),
          deductionsAPI.summary(regime),
        ]);
        if (!active) return;
        setRecords(discoveryResponse.data || []);
        setSummary(summaryResponse.data || null);
      } catch (loadError: unknown) {
        if (!active) return;
        const detail = (loadError as { response?: { status?: number } })?.response?.status === 404
          ? 'Add or complete your tax profile first. We use it to find deduction opportunities relevant to you.'
          : getErrorMessage(loadError);
        setError(detail);
        setRecords([]);
        setSummary(null);
        setProfile(null);
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();

    return () => {
      active = false;
    };
  }, [authHydrated, isAuthenticated, refreshKey, regime, router]);

  const claimedTotal = useMemo(
    () => (profile?.deductions || []).reduce((total, item) => total + amount(item.amount), 0),
    [profile],
  );

  const visibleRecords = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return records.filter((item) => {
      const matchesSearch = !normalizedSearch
        || item.section.toLowerCase().includes(normalizedSearch)
        || item.name.toLowerCase().includes(normalizedSearch)
        || item.explanation.toLowerCase().includes(normalizedSearch);
      const matchesStatus = statusFilter === 'all'
        || (statusFilter === 'review' && ['UNKNOWN', 'NEEDS_INFORMATION'].includes(item.status))
        || (statusFilter === 'claimed' && item.confirmed)
        || (statusFilter === 'unavailable' && ['NOT_ELIGIBLE', 'NOT_APPLICABLE'].includes(item.status));
      return matchesSearch && matchesStatus;
    });
  }, [records, search, statusFilter]);

  if (!authHydrated || !isAuthenticated) return null;

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Tax planning</p>
            <h1 className="mt-2 text-3xl font-bold">Deduction discovery</h1>
            <p className="mt-2 max-w-2xl text-sm text-[#64748B]">
              Review deductions already in your profile and information that may help determine eligibility.
              Estimates are based only on the details you have provided.
            </p>
          </div>
          <ReturnToDashboard />
        </header>

        <section className="mb-6 flex flex-col gap-4 rounded-2xl border border-[#D1FAE5] bg-[#ECFDF5] p-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#047857]">Assessment year {profile?.assessment_year || '2026-27'}</p>
            <p className="mt-1 text-sm text-[#334155]">Switch regimes to see which deduction rules apply to your current profile.</p>
          </div>
          <div className="inline-flex rounded-xl border border-[#A7F3D0] bg-white p-1" aria-label="Select tax regime">
            {(['old', 'new'] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={regime === option}
                onClick={() => setRegime(option)}
                className={`rounded-lg px-4 py-2 text-sm font-semibold capitalize ${
                  regime === option ? 'bg-[#064E3B] text-white' : 'text-[#475569] hover:bg-[#F1F5F9]'
                }`}
              >
                {option} regime
              </button>
            ))}
          </div>
        </section>

        {error && (
          <section className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-5" role="alert">
            <p className="font-semibold text-amber-900">{error}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href={needsProfile ? '/onboarding' : '/tax-profile'} className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
                Complete tax profile
              </Link>
              <button type="button" onClick={() => setRefreshKey((current) => current + 1)} className="rounded-xl border border-amber-300 bg-white px-4 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100">
                Try again
              </button>
            </div>
          </section>
        )}

        {loading ? (
          <section className="card p-8" aria-live="polite">
            <p className="font-semibold">Reviewing your deductions…</p>
            <p className="mt-2 text-sm text-[#64748B]">Checking profile details against the {regime} regime.</p>
          </section>
        ) : !error && summary ? (
          <>
            <section className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Deduction summary">
              <div className="card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748B]">Eligible amount identified</p>
                <p className="mt-3 text-2xl font-bold">{money(summary.potentialDeductions)}</p>
                <p className="mt-1 text-xs text-[#64748B]">Under the {regime} regime</p>
              </div>
              <div className="card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748B]">Claims in your profile</p>
                <p className="mt-3 text-2xl font-bold">{money(claimedTotal)}</p>
                <p className="mt-1 text-xs text-[#64748B]">Review each claim below</p>
              </div>
              <div className="card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748B]">Currently applied</p>
                <p className="mt-3 text-2xl font-bold">{money(summary.appliedDeductions)}</p>
                <p className="mt-1 text-xs text-[#64748B]">Calculated by the tax engine</p>
              </div>
              <div className="card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#64748B]">Need more details</p>
                <p className="mt-3 text-2xl font-bold">{summary.unknownCount + summary.needsInfoCount}</p>
                <p className="mt-1 text-xs text-[#64748B]">Potential items to review</p>
              </div>
            </section>

            <section>
              <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-xl font-bold">Your deduction opportunities</h2>
                  <p className="mt-1 text-sm text-[#64748B]">
                    {records.length} {records.length === 1 ? 'item' : 'items'} found for the {regime} regime.
                    {' '}Missing information does not mean you are ineligible.
                  </p>
                </div>
                {records.length > 0 && (
                  <div className="grid gap-2 sm:grid-cols-[minmax(200px,1fr)_190px]">
                    <label className="sr-only" htmlFor="deduction-search">Search deductions</label>
                    <input
                      id="deduction-search"
                      type="search"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Search name or section…"
                      className="rounded-xl border border-[#CBD5E1] bg-white px-3 py-2 text-sm"
                    />
                    <label className="sr-only" htmlFor="deduction-filter">Filter deductions</label>
                    <select
                      id="deduction-filter"
                      value={statusFilter}
                      onChange={(event) => setStatusFilter(event.target.value)}
                      className="rounded-xl border border-[#CBD5E1] bg-white px-3 py-2 text-sm"
                    >
                      <option value="all">All statuses</option>
                      <option value="review">Needs review</option>
                      <option value="claimed">In my profile</option>
                      <option value="unavailable">Unavailable</option>
                    </select>
                  </div>
                )}
              </div>

              {records.length === 0 ? (
                <div className="card p-8 text-center">
                  <h3 className="text-lg font-semibold">No deduction matches yet</h3>
                  <p className="mx-auto mt-2 max-w-xl text-sm text-[#64748B]">
                    Add income, savings, insurance, and other relevant details to your tax profile. We will only
                    show opportunities relevant to the information you provide.
                  </p>
                  <Link href="/tax-profile" className="mt-5 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
                    Review tax profile
                  </Link>
                </div>
              ) : visibleRecords.length === 0 ? (
                <div className="card p-8 text-center">
                  <p className="font-semibold">No deductions match these filters.</p>
                  <button type="button" onClick={() => { setSearch(''); setStatusFilter('all'); }} className="mt-3 text-sm font-semibold text-[#047857] hover:text-[#065F46]">
                    Clear filters
                  </button>
                </div>
              ) : (
                <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                  {visibleRecords.map((item) => (
                    <article key={item.section} className="card flex flex-col p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="text-lg font-bold">{item.name}</h3>
                          <p className="mt-1 text-xs font-semibold uppercase tracking-[0.12em] text-[#64748B]">{item.section}</p>
                        </div>
                        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${statusStyles[item.status] || statusStyles.UNKNOWN}`}>
                          {statusLabel(item.status)}
                        </span>
                      </div>

                      <dl className="mt-5 space-y-2 rounded-xl bg-[#F8FAFC] p-3 text-sm">
                        <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Claimed in profile</dt><dd className="font-semibold">{money(item.claimedAmount)}</dd></div>
                        <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Eligible amount</dt><dd className="font-semibold">{money(item.eligibleAmount)}</dd></div>
                        <div className="flex justify-between gap-4"><dt className="text-[#64748B]">Applied to calculation</dt><dd className="font-semibold">{money(item.appliedAmount)}</dd></div>
                      </dl>

                      <p className="mt-4 text-sm leading-6 text-[#334155]">{item.explanation}</p>

                      {item.requiredInformation.length > 0 && (
                        <div className="mt-4">
                          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#475569]">Information to check</p>
                          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#64748B]">
                            {item.requiredInformation.map((field) => <li key={field}>{field}</li>)}
                          </ul>
                        </div>
                      )}

                      {item.requiredDocuments.length > 0 && (
                        <div className="mt-4 border-t border-[#E2E8F0] pt-3">
                          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-[#475569]">Keep as evidence</p>
                          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[#64748B]">
                            {item.requiredDocuments.map((document) => <li key={document}>{document}</li>)}
                          </ul>
                        </div>
                      )}

                      {item.status !== 'NOT_APPLICABLE' && item.status !== 'NOT_ELIGIBLE' && (
                        <Link href="/tax-profile" className="mt-auto self-start pt-5 text-sm font-semibold text-[#047857] hover:text-[#065F46]">
                          Update in tax profile <span aria-hidden="true">→</span>
                        </Link>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </section>

            <p className="mt-8 rounded-xl border border-[#E2E8F0] bg-white p-4 text-xs leading-5 text-[#64748B]">
              This is a profile-based discovery aid, not a guarantee of eligibility or tax savings. Keep supporting
              records and confirm current rules before filing. Tax calculations remain subject to the details in your
              confirmed profile.
            </p>
          </>
        ) : null}
      </div>
    </main>
  );
};

export default DeductionsPage;
