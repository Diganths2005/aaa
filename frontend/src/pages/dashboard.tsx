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
  const { user, isAuthenticated, logout } = useAuthStore();
  const [documents, setDocuments] = useState<UserDocument[]>([]);
  const [documentMessage, setDocumentMessage] = useState('');
  const [itrMessage, setItrMessage] = useState('');
  const [checkingItr, setCheckingItr] = useState(false);
  const [profileReady, setProfileReady] = useState<boolean | null>(null);
  const [profile, setProfile] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const loadProfile = async () => {
      try {
        const response = await taxProfileAPI.getCurrentUser();
        setProfile(response.data);
        const comparisonResponse = await taxAPI.compareRegimes(response.data);
        setComparison(comparisonResponse.data);
        setProfileReady(true);
      } catch {
        setProfileReady(false);
        router.push('/onboarding');
      }
    };

    loadProfile();
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      documentsAPI.list().then((response) => setDocuments(response.data)).catch(() => undefined);
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  const formatCurrency = (amount: number) => `₹${(amount || 0).toLocaleString('en-IN')}`;

  const recommendedResult = comparison?.recommended_regime === 'old' ? comparison.old_regime : comparison?.new_regime;

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
    { label: 'Gross Total Income', value: formatCurrency(recommendedResult?.gross_total_income), change: 'Tax Engine result' },
    { label: 'Total Deductions', value: formatCurrency(recommendedResult?.total_deductions), change: 'Tax Engine result' },
    { label: 'Taxable Income', value: formatCurrency(recommendedResult?.taxable_income), change: 'Tax Engine result' },
    { label: 'Estimated Tax', value: formatCurrency(recommendedResult?.total_tax_liability), change: `${comparison?.recommended_regime || 'new'} regime` },
    { label: 'Taxes Paid', value: formatCurrency(recommendedResult?.total_tax_paid), change: 'Tax Engine result' },
    { label: 'Refund / Payable', value: recommendedResult?.refund > 0 ? formatCurrency(recommendedResult.refund) : formatCurrency(recommendedResult?.balance_payable), change: recommendedResult?.refund > 0 ? 'Refund' : 'Payable' },
  ];

  const insights = profile
    ? [
        'Your dashboard is based on the tax profile you confirmed.',
        'Review documents and deductions to keep your tax profile accurate.',
        'Use the tax profile builder if you need to add or correct information.',
      ]
    : [
        'Your profile has not been confirmed yet. Complete onboarding to unlock the dashboard.',
        'You can upload your documents or enter your information manually.',
      ];

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

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const handleDocumentSelection = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.type !== 'application/pdf') {
      setDocumentMessage('Please choose a PDF document.');
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
      const response = await itrAPI.eligibility();
      if (response.data.eligible) {
        setItrMessage('Based on your current Tax Profile, ITR-1 can be prepared.');
      } else {
        setItrMessage(`ITR-1 cannot currently be prepared because ${response.data.reasons.join(' ')}`);
      }
    } catch (error: any) {
      setItrMessage(error.response?.data?.detail || 'Complete and save your Tax Profile before preparing ITR-1.');
    } finally {
      setCheckingItr(false);
    }
  };

  const nextSteps = [
    'Review extracted document',
    'Review tax opportunities',
    'Compare regimes',
    'Run what-if simulation',
    'Resolve detected issue',
    'Complete Tax Profile',
    'Review ITR',
  ];

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
              <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Here&apos;s your current tax picture.</h1>
            </div>
            <div className="flex items-center gap-3">
              <button className="chip">AI summary ready</button>
              <Link href="/taxwise" className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">Ask TaxWise</Link>
            </div>
          </div>

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
                    <button key={step} className="flex w-full items-center justify-between rounded-2xl border border-border bg-white px-4 py-3 text-left text-sm font-medium text-[#0F172A] hover:border-[#10B981] hover:bg-[#ECFDF5]">
                      <span>{step}</span>
                      <span className="text-[#64748B]">→</span>
                    </button>
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
                  <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] p-4">
                    <div>
                      <p className="text-sm text-[#64748B]">Old Regime</p>
                      <p className="text-xl font-bold text-[#0F172A]">Awaiting calculation</p>
                    </div>
                    <span className="chip">Pending</span>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-[#ECFDF5] p-4">
                    <div>
                      <p className="text-sm text-[#64748B]">New Regime</p>
                      <p className="text-xl font-bold text-[#0F172A]">Awaiting calculation</p>
                    </div>
                    <span className="chip">Pending</span>
                  </div>
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
                <span>Upload PDF</span>
                <input type="file" accept="application/pdf" className="sr-only" onChange={handleDocumentSelection} />
              </label>
            </div>

            {documentMessage && <p className="mt-4 text-sm text-[#64748B]" role="status">{documentMessage}</p>}

            {documents.length > 0 ? (
              <ul className="mt-5 space-y-3">
                {documents.map((document) => (
                  <li key={document.id} className="flex items-center justify-between rounded-2xl border border-border bg-[#F8FAFC] px-4 py-3 text-sm">
                    <span className="font-medium text-[#0F172A]">{document.original_filename}</span>
                    <span className="text-[#64748B]">{document.status}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-border bg-[#F8FAFC] p-8 text-center text-sm text-[#64748B]">
                No documents uploaded yet. Upload a PDF for tax document intelligence and review.
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
    </div>
  );
};

export default DashboardPage;
