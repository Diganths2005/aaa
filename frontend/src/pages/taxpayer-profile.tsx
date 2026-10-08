import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { documentsAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { TaxProfile } from '@/types';
import { getProfileCompletion } from '@/lib/profile-completion';

type UploadedDocument = {
  id: string;
  original_filename: string;
  document_type: string;
  status: string;
  created_at?: string;
};

const money = (value: number | string | undefined) =>
  value === undefined || value === null
    ? 'Not provided'
    : `₹${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const valueOrMissing = (value: string | undefined) => value?.trim() || 'Not provided';

const TaxpayerProfilePage: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, hydrate } = useAuthStore();
  const [authHydrated, setAuthHydrated] = useState(false);
  const [profile, setProfile] = useState<TaxProfile | null>(null);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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
    Promise.all([taxProfileAPI.getCurrentUser(), documentsAPI.list()])
      .then(([profileResponse, documentsResponse]) => {
        if (!active) return;
        setProfile(profileResponse.data);
        setDocuments(documentsResponse.data || []);
      })
      .catch((loadError: unknown) => {
        if (!active) return;
        const status = (loadError as { response?: { status?: number } })?.response?.status;
        setError(status === 404
          ? 'No saved taxpayer profile was found yet. Complete your profile to see the full overview.'
          : 'We could not load your taxpayer profile. Please try again.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [authHydrated, isAuthenticated, router]);

  const taxPayments = useMemo(() => {
    if (!profile) return [];
    return (['tds', 'advance_tax', 'self_assessment'] as const).map((type) => ({
      type,
      amount: profile.taxes_paid
        .filter((payment) => payment.tax_type === type)
        .reduce((sum, payment) => sum + Number(payment.amount || 0), 0),
      count: profile.taxes_paid.filter((payment) => payment.tax_type === type).length,
    }));
  }, [profile]);
  const completion = getProfileCompletion(profile, documents.length);
  const sectionLinks = [
    ['personal', 'Personal Information'], ['employment', 'Employment'], ['salary-pension', 'Salary / Pension'],
    ['house-property', 'House Property'], ['other-income', 'Other Income'], ['capital-gains', 'Capital Gains'],
    ['deductions', 'Deductions'], ['tds', 'TDS'], ['advance-tax', 'Advance Tax'],
    ['self-assessment-tax', 'Self-Assessment Tax'], ['bank-accounts', 'Bank Accounts'],
    ['tax-documents', 'Tax Documents'], ['ais-26as', 'AIS / 26AS'], ['itr-information', 'ITR Information'],
  ];
  const editLink = (section: string) => `/tax-profile?section=${section}`;
  const editAction = (section: string) => <Link href={editLink(section)} className="print-hidden text-sm font-semibold text-[#047857] hover:text-[#065F46]">Edit</Link>;

  if (!authHydrated || !isAuthenticated) return null;

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Page 2 · Taxpayer profile</p>
            <h1 className="mt-2 text-3xl font-bold">Your taxpayer profile</h1>
            <p className="mt-2 text-sm text-[#64748B]">A report-ready overview of saved values. Fields that have not been provided are shown as missing, not inferred.</p>
          </div>
          <div className="print-hidden flex flex-wrap gap-3">
            <Link href="/dashboard" className="inline-flex items-center justify-center rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold text-[#334155] hover:bg-[#F1F5F9]">
              Return to dashboard
            </Link>
            <button type="button" onClick={() => window.print()} className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold text-[#334155] hover:bg-[#F1F5F9]">
              Print profile
            </button>
            <Link href="/tax-profile" className="inline-flex items-center justify-center rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
              Edit profile
            </Link>
          </div>
        </header>

        {loading ? (
          <section className="card p-8" aria-live="polite">Loading your saved taxpayer information…</section>
        ) : error ? (
          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-6" role="alert">
            <p className="font-semibold text-amber-900">{error}</p>
            <Link href="/tax-profile" className="print-hidden mt-4 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
              Complete taxpayer profile
            </Link>
          </section>
        ) : profile ? (
          <>
            <nav className="mb-6 card p-4" aria-label="Tax profile sections">
              <p className="mb-3 text-sm font-semibold">Profile sections</p>
              <div className="flex flex-wrap gap-2">{sectionLinks.map(([section, label]) => <a key={section} href={`#${section}`} className="rounded-full border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs font-medium text-[#334155] hover:border-[#10B981]">{label}</a>)}</div>
            </nav>
            <section className="mb-6 rounded-3xl border border-[#D1FAE5] bg-white p-6 shadow-soft">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#047857]">Taxpayer</p>
                  <h2 className="mt-2 text-2xl font-bold">{[user?.firstName, user?.lastName].filter(Boolean).join(' ') || 'Taxpayer'}</h2>
                  <p className="mt-1 text-sm text-[#64748B]">{user?.email || 'Email not available'}</p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-2xl bg-[#F8FAFC] px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-[#64748B]">Assessment year</p>
                    <p className="mt-1 font-semibold">{profile.assessment_year}</p>
                  </div>
                  <div className="rounded-2xl bg-[#F8FAFC] px-4 py-3">
                    <p className="text-xs uppercase tracking-wide text-[#64748B]">Residential status</p>
                    <p className="mt-1 font-semibold capitalize">{profile.residential_status ? profile.residential_status.replace(/_/g, ' ') : 'Not provided'}</p>
                  </div>
                </div>
              </div>
              <div className="mt-5">
                <div className="mb-2 flex items-center justify-between text-sm"><span className="font-semibold">Profile completion</span><strong className="text-[#047857]">{completion.percent}%</strong></div>
                <div className="h-2 overflow-hidden rounded-full bg-[#E2E8F0]" role="progressbar" aria-valuenow={completion.percent} aria-valuemin={0} aria-valuemax={100}><div className="h-full bg-[#047857]" style={{ width: `${completion.percent}%` }} /></div>
              </div>
            </section>

            <div className="grid gap-5 md:grid-cols-2">
              <section id="personal" className="card p-6 print-break-inside-avoid" aria-labelledby="personal-heading">
                <div className="flex items-center justify-between"><h2 id="personal-heading" className="text-lg font-bold">Personal information</h2>{editAction('personal')}</div>
                <dl className="mt-4 grid grid-cols-2 gap-x-5 gap-y-4 text-sm">
                  <div><dt className="text-[#64748B]">Date of birth</dt><dd className="mt-1 font-medium">{valueOrMissing(profile.date_of_birth)}</dd></div>
                  <div><dt className="text-[#64748B]">PAN</dt><dd className="mt-1 font-medium">{valueOrMissing(profile.pan_number)}</dd></div>
                  <div className="col-span-2"><dt className="text-[#64748B]">Address</dt><dd className="mt-1 font-medium">{[profile.address, profile.city, profile.state, profile.pincode].filter(Boolean).join(', ') || 'Not provided'}</dd></div>
                </dl>
              </section>

              <section id="employment" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">Employment</h2>{editAction('employment')}</div>
                <dl className="mt-4 space-y-3 text-sm"><div><dt className="text-[#64748B]">Work situation</dt><dd className="font-medium capitalize">{profile.employment_type || 'Not provided'}</dd></div><div><dt className="text-[#64748B]">Employer</dt><dd className="font-medium">{valueOrMissing(profile.employer_name)}</dd></div><div><dt className="text-[#64748B]">Employer address</dt><dd className="font-medium">{valueOrMissing(profile.employer_address)}</dd></div></dl>
              </section>

              <section id="salary-pension" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">Salary / Pension</h2>{editAction('salary-pension')}</div>
                {[...profile.salary_income.map((item) => ({ label: `Salary · ${item.employer_name}`, amount: item.gross_salary })), ...profile.pension_income.map((item) => ({ label: `Pension · ${item.payer_name}`, amount: item.amount }))].length ? (
                  <ul className="mt-4 divide-y divide-[#E2E8F0]">{[...profile.salary_income.map((item) => ({ label: `Salary · ${item.employer_name}`, amount: item.gross_salary })), ...profile.pension_income.map((item) => ({ label: `Pension · ${item.payer_name}`, amount: item.amount }))].map((item) => <li key={item.label} className="flex justify-between gap-3 py-3 text-sm"><span>{item.label}</span><strong>{money(item.amount)}</strong></li>)}</ul>
                ) : <p className="mt-4 text-sm text-[#64748B]">No salary or pension information has been provided.</p>}
                <p className="mt-3 text-xs text-[#64748B]">Saved profile value · field-level document provenance is not stored by the current profile API.</p>
              </section>

              <section id="house-property" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">House Property</h2>{editAction('house-property')}</div>
                {profile.house_properties.length ? <ul className="mt-4 space-y-3">{profile.house_properties.map((property, index) => <li key={`${property.city}-${index}`} className="rounded-xl bg-[#F8FAFC] p-4 text-sm"><p className="font-semibold capitalize">{property.property_type.replace(/_/g, ' ')} · {property.city}</p><p className="mt-2 text-[#64748B]">Annual rent: {money(property.annual_rent)} · Loan interest: {money(property.home_loan_interest)}</p></li>)}</ul> : <p className="mt-4 text-sm text-[#64748B]">No house-property details have been provided.</p>}
              </section>

              <section id="other-income" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">Other Income</h2>{editAction('other-income')}</div>
                {profile.other_income.length ? <ul className="mt-4 divide-y divide-[#E2E8F0]">{profile.other_income.map((item, index) => <li key={`${item.income_type}-${index}`} className="flex justify-between gap-3 py-3 text-sm"><span className="capitalize">{item.description || item.income_type}</span><strong>{money(item.amount)}</strong></li>)}</ul> : <p className="mt-4 text-sm text-[#64748B]">No other income information has been provided.</p>}
              </section>

              <section id="capital-gains" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">Capital Gains</h2>{editAction('capital-gains')}</div>
                {profile.capital_gains.length ? <ul className="mt-4 space-y-3">{profile.capital_gains.map((gain, index) => <li key={`${gain.asset_type}-${index}`} className="rounded-xl bg-[#F8FAFC] p-4 text-sm"><p className="font-semibold capitalize">{gain.asset_type.replace(/_/g, ' ')}</p><p className="mt-2 text-[#64748B]">Purchase: {gain.acquisition_date || 'Not provided'} · Sale: {gain.sale_date || 'Not provided'}</p><p className="mt-1 text-[#64748B]">Purchase price: {money(gain.acquisition_cost)} · Sale price: {money(gain.sale_consideration)}</p></li>)}</ul> : <p className="mt-4 text-sm text-[#64748B]">No capital-gains transactions have been provided.</p>}
                <p className="mt-3 text-xs text-[#64748B]">Tax treatment is calculated by the TaxWise Engine when supported; this profile overview does not estimate gains.</p>
              </section>

              <section id="deductions" className="card p-6 print-break-inside-avoid" aria-labelledby="deduction-heading">
                <div className="flex items-center justify-between gap-3">
                  <h2 id="deduction-heading" className="text-lg font-bold">Deductions</h2>
                  <div className="flex gap-3">{editAction('deductions')}<Link href="/deductions" className="print-hidden text-sm font-semibold text-[#047857] hover:text-[#065F46]">Review eligibility →</Link></div>
                </div>
                {profile.deductions.length ? (
                  <ul className="mt-4 divide-y divide-[#E2E8F0]">
                    {profile.deductions.map((deduction, index) => (
                      <li key={`${deduction.section}-${index}`} className="flex items-center justify-between gap-4 py-3 text-sm">
                        <span className="text-[#475569]">{deduction.section}</span>
                        <span className="font-semibold">{money(deduction.amount)}</span>
                      </li>
                    ))}
                    <li className="flex items-center justify-between gap-4 py-3 text-sm font-bold">
                      <span>Total claims in profile</span>
                      <span>{money(profile.deductions.reduce((sum, deduction) => sum + Number(deduction.amount || 0), 0))}</span>
                    </li>
                  </ul>
                ) : <p className="mt-4 text-sm text-[#64748B]">No deduction claims have been added to the profile.</p>}
              </section>

              <section id="tds" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">TDS</h2>{editAction('tds')}</div>
                <p className="mt-4 text-2xl font-bold">{money(taxPayments.find((item) => item.type === 'tds')?.amount || undefined)}</p><p className="mt-1 text-sm text-[#64748B]">Profile-recorded TDS · no reconciliation is implied.</p>
              </section>

              <section id="advance-tax" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">Advance Tax</h2>{editAction('advance-tax')}</div>
                <p className="mt-4 text-2xl font-bold">{money(taxPayments.find((item) => item.type === 'advance_tax')?.amount || undefined)}</p>
              </section>

              <section id="self-assessment-tax" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">Self-Assessment Tax</h2>{editAction('self-assessment-tax')}</div>
                <p className="mt-4 text-2xl font-bold">{money(taxPayments.find((item) => item.type === 'self_assessment')?.amount || undefined)}</p>
              </section>

              <section id="bank-accounts" className="card p-6 print-break-inside-avoid" aria-labelledby="bank-heading">
                <div className="flex items-center justify-between"><h2 id="bank-heading" className="text-lg font-bold">Bank accounts</h2>{editAction('bank-accounts')}</div>
                {profile.bank_accounts.length ? (
                  <ul className="mt-4 space-y-3">
                    {profile.bank_accounts.map((account, index) => (
                      <li key={`${account.bank_name}-${index}`} className="rounded-xl bg-[#F8FAFC] p-4 text-sm">
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-semibold">{account.bank_name}</p>
                          {account.is_primary && <span className="rounded-full bg-[#ECFDF5] px-2 py-1 text-xs font-semibold text-[#047857]">Primary</span>}
                        </div>
                        <p className="mt-1 text-[#64748B]">{account.account_type.toUpperCase()} · {account.account_number}</p>
                        <p className="mt-1 text-xs text-[#64748B]">IFSC: {account.ifsc_code}</p>
                      </li>
                    ))}
                  </ul>
                ) : <p className="mt-4 text-sm text-[#64748B]">No bank accounts have been added.</p>}
              </section>

              <section id="tax-documents" className="card p-6 print-break-inside-avoid" aria-labelledby="uploaded-documents-heading">
                <div className="flex items-center justify-between"><h2 id="uploaded-documents-heading" className="text-lg font-bold">Tax Documents</h2>{editAction('tax-documents')}</div>
                {documents.length ? (
                  <ul className="mt-4 space-y-2">
                    {documents.slice(0, 6).map((document) => (
                      <li key={document.id} className="flex items-center justify-between gap-3 rounded-xl bg-[#F8FAFC] px-3 py-3 text-sm">
                        <span className="min-w-0 truncate font-medium">{document.original_filename}</span>
                        <span className="shrink-0 text-xs text-[#64748B]">{document.status.replace(/_/g, ' ')}</span>
                      </li>
                    ))}
                  </ul>
                ) : <p className="mt-4 text-sm text-[#64748B]">No documents have been uploaded.</p>}
                <Link href="/documents" className="print-hidden mt-4 inline-flex text-sm font-semibold text-[#047857] hover:text-[#065F46]">
                  Manage documents →
                </Link>
              </section>

              <section id="ais-26as" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">AIS / 26AS</h2>{editAction('ais-26as')}</div>
                {documents.filter((document) => ['ais_tis', 'form_26as'].includes(document.document_type)).length
                  ? <ul className="mt-4 space-y-2">{documents.filter((document) => ['ais_tis', 'form_26as'].includes(document.document_type)).map((document) => <li key={document.id} className="flex justify-between gap-3 rounded-xl bg-[#F8FAFC] p-3 text-sm"><span>{document.original_filename} · {document.document_type === 'ais_tis' ? 'AIS' : '26AS'}</span><span className="text-xs text-[#64748B]">{document.status.replace(/_/g, ' ')}</span></li>)}</ul>
                  : <p className="mt-4 text-sm text-[#64748B]">No AIS or 26AS documents have been uploaded.</p>}
                <Link href="/reconciliation" className="print-hidden mt-4 inline-flex text-sm font-semibold text-[#047857]">Open reconciliation →</Link>
              </section>

              <section id="itr-information" className="card p-6 print-break-inside-avoid">
                <div className="flex items-center justify-between"><h2 className="text-lg font-bold">ITR Information</h2>{editAction('itr-information')}</div>
                <p className="mt-4 text-sm text-[#475569]">Assessment year: <strong>{profile.assessment_year || 'Not provided'}</strong></p>
                <p className="mt-2 text-sm text-[#64748B]">ITR eligibility and preparation support are determined from the saved profile by the backend service.</p>
                <Link href="/itr-selection" className="print-hidden mt-4 inline-flex text-sm font-semibold text-[#047857]">View ITR selection →</Link>
              </section>
            </div>

            <footer className="mt-6 flex flex-col gap-3 rounded-2xl border border-[#E2E8F0] bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-[#64748B]">Profile values are for review and may need supporting documents before filing.</p>
              <Link href="/tax-profile" className="print-hidden inline-flex justify-center rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
                Edit or update profile
              </Link>
            </footer>
          </>
        ) : null}
      </div>
    </main>
  );
};

export default TaxpayerProfilePage;
