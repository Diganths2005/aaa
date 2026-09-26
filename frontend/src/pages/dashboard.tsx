import React, { ChangeEvent, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';
import { documentsAPI, itrAPI, taxAPI, taxProfileAPI } from '@/lib/api';

type UserDocument = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
  created_at?: string;
  processing_result?: { candidates?: Array<{ field: string; value: string }> };
};

const navItems = [
  { label: 'Home', href: '/dashboard', icon: '🏠', active: true },
  { label: 'What-If', href: '/what-if', icon: '🧮', active: false },
  { label: 'Compare Regimes', href: '/compare-regimes', icon: '⚖', active: false },
  { label: 'TaxWise', href: '/taxwise', icon: '💬', active: false },
  { label: 'Documents', href: '/documents', icon: '📄', active: false },
  { label: 'Deductions', href: '/deductions', icon: '💰', active: false },
  { label: 'My Tax Profile', href: '/tax-profile', icon: '👤', active: false },
  { label: 'File ITR', href: '/itr-preview', icon: '🧾', active: false },
];

const DashboardPage: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, hydrate, logout } = useAuthStore();
  const [authHydrated, setAuthHydrated] = useState(false);
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [documentMessage, setDocumentMessage] = useState('');
  const [itrMessage, setItrMessage] = useState('');
  const [checkingItr, setCheckingItr] = useState(false);
  const [profileReady, setProfileReady] = useState<boolean | null>(null);
  const [profile, setProfile] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);
  const [itrSelection, setItrSelection] = useState<any>(null);

  useEffect(() => {
    hydrate();
    setAuthHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (!authHydrated) return;
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const loadProfile = async () => {
      try {
        const response = await taxProfileAPI.getCurrentUser();
        setProfile(response.data);
        const comparisonResponse = await taxAPI.compareRegimes(response.data, true);
        setComparison(comparisonResponse.data);
        const itrResponse = await itrAPI.selection();
        setItrSelection(itrResponse.data);
        setProfileReady(true);
      } catch {
        setProfileReady(false);
        router.push('/onboarding');
      }
    };

    loadProfile();
  }, [authHydrated, isAuthenticated, router]);

  useEffect(() => {
    if (authHydrated && isAuthenticated) {
      documentsAPI.list().then((response) => setDocuments(response.data)).catch(() => undefined);
    }
  }, [authHydrated, isAuthenticated]);

  const formatCurrency = (amount: number | string | undefined) => `₹${Number(amount || 0).toLocaleString('en-IN')}`;

  const recommendedResult = comparison?.recommended_regime === 'old' ? comparison.old_regime : comparison?.new_regime;
  const confirmedDeductions = useMemo(
    () => (profile?.deductions || []).reduce((sum: number, item: any) => sum + Number(item.amount || 0), 0),
    [profile]
  );

  const incomeBreakdown = useMemo(() => {
    if (!profile) return [] as Array<{ name: string; amount: number; percent: number }>;

    const salary = (profile.salary_income || []).reduce((sum: number, item: any) => sum + Number(item.gross_salary || 0), 0);
    const property = (profile.house_properties || []).reduce((sum: number, item: any) => sum + Number(item.annual_rent || 0), 0);
    const other = (profile.other_income || []).reduce((sum: number, item: any) => sum + Number(item.amount || 0), 0);
    const capital = (profile.capital_gains || []).reduce((sum: number, item: any) => sum + Number(item.gain_or_loss || 0), 0);
    const pension = (profile.pension_income || []).reduce((sum: number, item: any) => sum + Number(item.amount || 0), 0);
    const entries = [
      { name: 'Salary', amount: salary },
      { name: 'Pension', amount: pension },
      { name: 'House Property', amount: property },
      { name: 'Other Income', amount: other },
      { name: 'Capital Gains', amount: capital },
    ].filter((item) => item.amount > 0);

    const total = entries.reduce((sum, item) => sum + item.amount, 0) || 1;
    return entries.map((item) => ({ ...item, percent: (item.amount / total) * 100 }));
  }, [profile]);

  const metrics = [
    { label: 'Gross Total Income', value: formatCurrency(recommendedResult?.gross_total_income), change: 'Current calculation' },
    { label: 'Total Deductions', value: formatCurrency(confirmedDeductions), change: 'Confirmed profile deductions' },
    { label: 'Taxable Income', value: formatCurrency(recommendedResult?.taxable_income), change: 'Current calculation' },
    { label: 'Estimated Tax', value: formatCurrency(recommendedResult?.total_tax_liability), change: `${comparison?.recommended_regime || 'new'} regime` },
    { label: 'Taxes Paid', value: formatCurrency(recommendedResult?.total_tax_paid), change: 'Current calculation' },
    { label: 'Refund / Payable', value: recommendedResult?.refund > 0 ? formatCurrency(recommendedResult.refund) : formatCurrency(recommendedResult?.balance_payable), change: recommendedResult?.refund > 0 ? 'Refund' : 'Payable' },
  ];

  const insights = useMemo(() => {
    if (!profile) {
      return [
        'Your profile has not been confirmed yet. Complete onboarding to unlock the dashboard.',
        'You can upload your documents or enter your information manually.',
      ];
    }

    const salary = (profile.salary_income || []).reduce((sum: number, item: any) => sum + Number(item.gross_salary || 0), 0);
    const deductions = (profile.deductions || []).reduce((sum: number, item: any) => sum + Number(item.amount || 0), 0);
    const items = [
      `Your tax profile currently reflects ₹${salary.toLocaleString('en-IN')} in salary income across ${profile.salary_income?.length || 0} source entries.`,
      `Confirmed deductions total ₹${deductions.toLocaleString('en-IN')}. Review them if you want to maximize eligible savings.`,
    ];

    if (comparison) {
      const regimeLabel = comparison.recommended_regime === 'old' ? 'Old Regime' : comparison.recommended_regime === 'new' ? 'New Regime' : 'Both regimes are effectively similar';
      const estimatedSaving = Number(comparison.estimated_saving || 0);
      items.push(
        `${regimeLabel} is recommended for AY ${profile.assessment_year || '2026-27'} with an estimated saving of ₹${estimatedSaving.toLocaleString('en-IN')}.`
      );
    }

    if (documents.length === 0) {
      items.push('No documents are uploaded yet. Add a PDF to improve document intelligence and filing confidence.');
    }

    return items;
  }, [comparison, documents.length, profile]);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleDocumentSelection = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    const supported = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xlsm');
    if (!supported) {
      setDocumentMessage('Please choose a PDF or Excel document.');
      return;
    }

    try {
      const uploaded = await documentsAPI.upload(file, '2026-27');
      const processed = await documentsAPI.process(uploaded.data.id);
      setDocuments((current) => [{ ...uploaded.data, status: processed.data.status }, ...current]);
      setDocumentMessage(processed.data.candidates?.length ? 'Document processed. Open Documents to review extracted values before confirmation.' : 'Document processed, but no supported tax fields were found.');
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      setDocumentMessage(detail === 'DOCUMENT_REQUIRES_OCR' ? 'This PDF is scanned and needs OCR, which is not available yet.' : 'Document processing failed. No profile data was changed.');
    }
  };

  const handleFileItr = async () => {
    setCheckingItr(true);
    setItrMessage("Let's check your ITR eligibility.");
    try {
      const response = await itrAPI.selection();
      if (response.data.eligible && response.data.recommended_itr) {
        setItrMessage(`Based on your current Tax Profile, ${response.data.recommended_itr} is recommended.`);
      } else {
        const reasons = [...(response.data.reasons || []), ...(response.data.missing_information || []), ...(response.data.unsupported_conditions || [])];
        setItrMessage(`An ITR form is not ready yet. ${reasons.join(' ')}`);
      }
    } catch (error: any) {
      setItrMessage(error.response?.data?.detail || 'Complete and save your Tax Profile before preparing a return.');
    } finally {
      setCheckingItr(false);
    }
  };

  const nextSteps = useMemo(() => {
    const items = [
      { label: 'Review tax profile', href: '/tax-profile', enabled: !!profile },
      { label: 'Upload documents', href: '/documents', enabled: true },
      { label: 'Compare regimes', href: '/compare-regimes', enabled: !!comparison },
      { label: 'Run what-if simulation', href: '/what-if', enabled: !!profile },
      { label: 'Ask TaxWise', href: '/taxwise', enabled: true },
      { label: 'Review ITR', href: '/itr-preview', enabled: !!profile },
    ];

    return items;
  }, [comparison, profile]);

  const journey = useMemo(() => {
    const completed = [
      { label: 'Profile', done: !!profile, detail: profile ? 'Information confirmed' : 'Needs attention' },
      { label: 'Documents', done: documents.length > 0, detail: documents.length ? `${documents.length} uploaded` : 'Upload a PDF' },
      { label: 'Tax calc', done: !!comparison, detail: comparison ? 'Ready' : 'Pending' },
      { label: 'Deductions', done: !!profile && (profile.deductions?.length || 0) > 0, detail: profile && (profile.deductions?.length || 0) > 0 ? 'Review available' : 'Check eligibility' },
      { label: 'ITR', done: !!itrSelection?.eligible, detail: itrSelection?.recommended_itr || (profile ? 'Review needed' : 'Not started') },
    ];

    return completed;
  }, [comparison, documents.length, itrSelection, profile]);

  if (profileReady === false) {
    return (
      <div className="min-h-screen bg-[#F8FAFC] px-4 py-12 text-[#0F172A]">
        <div className="mx-auto max-w-2xl rounded-[28px] border border-[#E2E8F0] bg-white p-8 shadow-soft">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TaxWise</p>
          <h1 className="mt-4 text-3xl font-bold">Your tax profile is not ready yet.</h1>
          <p className="mt-4 text-base text-[#64748B]">
            New users should complete the onboarding flow before they see personalized dashboard data.
          </p>
          <button
            type="button"
            onClick={() => router.push('/onboarding')}
            className="mt-6 rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white hover:bg-[#065F46]"
          >
            Continue onboarding
          </button>
        </div>
      </div>
    );
  }

  if (!authHydrated || !isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A]">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 bg-[#064E3B] p-6 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 border-b border-white/10 pb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#10B981] text-lg font-bold text-[#064E3B]">T</div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100">TaxWise</p>
              <p className="text-sm text-emerald-50/80">Personal Tax Intelligence</p>
            </div>
          </div>

          <nav className="mt-8 space-y-1.5">
            {navItems.map((item) => (
              <Link key={item.label} href={item.href} className={`sidebar-link ${item.active ? 'active' : ''}`}>
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="mt-auto space-y-2 border-t border-white/10 pt-6">
            <button className="sidebar-link w-full justify-start">
              <span>⚙</span>
              <span>Settings</span>
            </button>
            <button onClick={handleLogout} className="sidebar-link w-full justify-start">
              <span>↪</span>
              <span>Logout</span>
            </button>
          </div>
        </aside>

        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <div className="mb-6 flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Good morning, {user?.firstName || 'Taxpayer'}</p>
              <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Your tax journey is ready.</h1>
            </div>
            <div className="flex items-center gap-3">
              <button className="chip">{profile ? 'Profile synced' : 'Profile pending'}</button>
              <Link href="/taxwise" className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">Ask TaxWise</Link>
            </div>
          </div>

          <div className="mb-6 rounded-[24px] border border-[#E2E8F0] bg-white p-4 shadow-soft">
            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Journey progress</p>
              <span className="text-xs font-medium text-[#64748B]">{journey.filter((step) => step.done).length}/{journey.length} done</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
              {journey.map((step) => (
                <div key={step.label} className={`rounded-2xl border p-3 ${step.done ? 'border-[#C7F9D9] bg-[#ECFDF5]' : 'border-[#E2E8F0] bg-[#F8FAFC]'}`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-[0.16em] text-[#64748B]">{step.label}</span>
                    <span className={`h-2.5 w-2.5 rounded-full ${step.done ? 'bg-[#047857]' : 'bg-[#CBD5E1]'}`} />
                  </div>
                  <p className="mt-2 text-sm font-medium text-[#0F172A]">{step.detail}</p>
                </div>
              ))}
            </div>
          </div>

          {profile && (
            <div className="mb-6 grid gap-4 sm:grid-cols-2">
              <div className="card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#047857]">Date of birth</p>
                <p className="mt-3 text-lg font-semibold text-[#0F172A]">{profile.date_of_birth || 'Not provided'}</p>
              </div>
              <div className="card p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#047857]">PAN number</p>
                <p className="mt-3 text-lg font-semibold uppercase text-[#0F172A]">{profile.pan_number || 'Not provided'}</p>
              </div>
            </div>
          )}

          {!profile && (
            <div className="mb-6 rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] p-4 text-sm text-[#047857]">
              Your dashboard is ready, and it will update as soon as your tax profile is confirmed.
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {metrics.map((metric) => (
              <div key={metric.label} className="metric-card">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-[#64748B]">{metric.label}</p>
                  <span className="rounded-full bg-[#ECFDF5] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#047857]">Live</span>
                </div>
                <p className="mt-4 text-3xl font-bold text-[#0F172A]">{metric.value}</p>
                <p className="mt-2 text-sm text-[#047857]">{metric.change}</p>
              </div>
            ))}
          </div>

          {profile && (
            <div className="mt-8 grid gap-6 xl:grid-cols-[1.5fr_0.9fr]">
              <div className="card p-6">
                <div className="mb-5 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TaxWise Insights</p>
                    <h2 className="mt-2 text-xl font-bold text-[#0F172A]">What TaxWise found</h2>
                  </div>
                  <button className="rounded-full border border-border bg-[#ECFDF5] px-3 py-1.5 text-xs font-semibold text-[#047857]">{insights.length} items</button>
                </div>

                <div className="space-y-4">
                  {insights.map((item, index) => (
                    <div key={item} className="rounded-2xl border border-border bg-[#F8FAFC] p-4">
                      <div className="flex items-start gap-3">
                        <span className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-full bg-[#ECFDF5] text-sm text-[#047857]">
                          {index % 2 === 0 ? '✓' : '⚠'}
                        </span>
                        <div>
                          <p className="text-sm font-semibold text-[#0F172A]">{item}</p>
                          <p className="mt-1 text-sm text-[#64748B]">This recommendation is based on the profile details you have confirmed.</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">What&apos;s next?</p>
                <h2 className="mt-2 text-xl font-bold text-[#0F172A]">Smart actions</h2>
                <div className="mt-5 space-y-3">
                  {nextSteps.map((step) => (
                    <Link
                      key={step.label}
                      href={step.enabled ? step.href : '#'}
                      onClick={(event) => {
                        if (!step.enabled) {
                          event.preventDefault();
                        }
                      }}
                      className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left text-sm font-medium transition ${
                        step.enabled
                          ? 'border-border bg-white text-[#0F172A] hover:border-[#10B981] hover:bg-[#ECFDF5]'
                          : 'cursor-not-allowed border-dashed border-[#CBD5E1] bg-[#F8FAFC] text-[#94A3B8]'
                      }`}
                    >
                      <span>{step.label}</span>
                      <span className="text-[#64748B]">{step.enabled ? '→' : '•'}</span>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          )}

          {profile && (
            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <div className="card p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Income breakdown</p>
                <div className="mt-5 space-y-4">
                  {incomeBreakdown.length > 0 ? (
                    incomeBreakdown.map((item) => (
                      <div key={item.name}>
                        <div className="mb-1 flex items-center justify-between text-sm text-[#64748B]">
                          <span>{item.name}</span>
                          <span>{Math.round(item.percent)}%</span>
                        </div>
                        <div className="h-2.5 w-full rounded-full bg-[#ECFDF5]">
                          <div className="h-2.5 rounded-full bg-[#047857]" style={{ width: `${item.percent}%` }} />
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-[#64748B]">Add income details to see your breakdown on this dashboard.</p>
                  )}
                </div>
              </div>

              <div className="card p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Regime comparison</p>
                <div className="mt-6 space-y-4">
                  {comparison ? (
                    <>
                      {[
                        {
                          label: 'Old Regime',
                          amount: formatCurrency(comparison.old_regime.total_tax_liability),
                          tone: comparison.recommended_regime === 'old' ? 'bg-[#ECFDF5]' : 'bg-[#F8FAFC]',
                          badge: comparison.recommended_regime === 'old' ? 'Recommended' : 'Alternative',
                        },
                        {
                          label: 'New Regime',
                          amount: formatCurrency(comparison.new_regime.total_tax_liability),
                          tone: comparison.recommended_regime === 'new' ? 'bg-[#ECFDF5]' : 'bg-[#F8FAFC]',
                          badge: comparison.recommended_regime === 'new' ? 'Recommended' : 'Alternative',
                        },
                      ].map((regime) => (
                        <div key={regime.label} className={`flex items-center justify-between rounded-2xl p-4 ${regime.tone}`}>
                          <div>
                            <p className="text-sm text-[#64748B]">{regime.label}</p>
                            <p className="text-xl font-bold text-[#0F172A]">{regime.amount}</p>
                          </div>
                          <span className="chip">{regime.badge}</span>
                        </div>
                      ))}
                    </>
                  ) : (
                    <>
                      <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] p-4">
                        <div>
                          <p className="text-sm text-[#64748B]">Old Regime</p>
                          <p className="text-xl font-bold text-[#0F172A]">Complete your tax profile</p>
                        </div>
                        <span className="chip">Pending</span>
                      </div>
                      <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] p-4">
                        <div>
                          <p className="text-sm text-[#64748B]">New Regime</p>
                          <p className="text-xl font-bold text-[#0F172A]">Complete your tax profile</p>
                        </div>
                        <span className="chip">Pending</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          <section className="mt-8 card p-6" aria-labelledby="documents-heading">
            <div className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Documents</p>
                <h3 id="documents-heading" className="mt-2 text-xl font-bold text-[#0F172A]">My documents</h3>
              </div>
              <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
                <span>Upload PDF or Excel</span>
                <input type="file" accept="application/pdf,.xlsx,.xlsm" className="sr-only" onChange={handleDocumentSelection} />
              </label>
            </div>

            {documentMessage && <p className="mt-4 text-sm text-[#64748B]" role="status">{documentMessage}</p>}

            {documents.length > 0 ? (
              <ul className="mt-5 space-y-3">
                {documents.map((document) => (
                  <li key={document.id} className="rounded-2xl border border-border bg-[#F8FAFC] px-4 py-3 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-medium text-[#0F172A]">{document.original_filename}</span>
                      <span className="text-[#64748B]">{document.status}</span>
                    </div>
                    {document.processing_result?.candidates?.length ? (
                      <div className="mt-3 grid gap-1 border-t border-border pt-3 text-xs text-[#475569] sm:grid-cols-2">
                        {document.processing_result.candidates.map((candidate, index) => (
                          <span key={`${candidate.field}-${index}`}><strong>{candidate.field.replace(/_/g, ' ')}:</strong> {candidate.value}</span>
                        ))}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-border bg-[#F8FAFC] p-8 text-center text-sm text-[#64748B]">
                No documents uploaded yet. Upload a PDF or Excel sheet for tax document intelligence and review.
              </div>
            )}

            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button onClick={handleFileItr} disabled={checkingItr} className="rounded-xl bg-[#064E3B] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#022C22] disabled:opacity-60">
                {checkingItr ? 'Checking ITR readiness...' : 'Check ITR readiness'}
              </button>
              {itrMessage && (
                <Link href="/itr-preview" className="rounded-xl border border-[#10B981] bg-[#ECFDF5] px-4 py-2.5 text-sm font-semibold text-[#047857] hover:bg-[#DCFCE7]">
                  Review ITR
                </Link>
              )}
            </div>
            {itrMessage && <p className="mt-4 text-sm text-[#64748B]">{itrMessage}</p>}
          </section>
        </main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-[#E2E8F0] bg-white/95 px-2 py-2 backdrop-blur sm:hidden">
        <div className="flex items-center justify-around gap-1">
          {navItems.slice(0, 5).map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={`flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-2 py-2 text-[10px] font-medium ${item.active ? 'bg-[#ECFDF5] text-[#047857]' : 'text-[#64748B]'}`}
            >
              <span>{item.icon}</span>
              <span className="truncate">{item.label === 'My Tax Profile' ? 'Profile' : item.label}</span>
            </Link>
          ))}
        </div>
      </nav>
    </div>
  );
};

export default DashboardPage;
