import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { documentsAPI, taxProfileAPI } from '@/lib/api';
import { getProfileCompletion } from '@/lib/profile-completion';
import { useAuthStore } from '@/store/auth';
import { TaxProfile } from '@/types';

type Candidate = { field: string; value: string };
type TaxDocument = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
  processing_result?: { candidates?: Candidate[] };
};
type Source = 'form_16' | 'ais_tis' | 'form_26as';
type RowKey = 'salary' | 'tds' | 'interest';
type ReconciliationRow = {
  key: RowKey;
  label: string;
  form16?: number;
  ais?: number;
  form26as?: number;
  profile?: number;
  documentPending: boolean;
  candidates: Partial<Record<Source, Candidate>>;
};

const readCandidate = (documents: TaxDocument[], source: Source, field: string) => {
  const document = documents.find((item) => item.document_type === source && item.status !== 'REJECTED' && item.processing_result?.candidates?.some((candidate) => candidate.field === field));
  const candidate = document?.processing_result?.candidates?.find((item) => item.field === field);
  return document && candidate ? { document, candidate } : undefined;
};

const toNumber = (value: string | number | undefined) => {
  if (value === undefined) return undefined;
  const parsed = Number(String(value).replace(/[₹,\s]/g, ''));
  return Number.isFinite(parsed) ? parsed : undefined;
};
const money = (value: number | undefined) => value === undefined ? '—' : `₹${value.toLocaleString('en-IN')}`;

const ReconciliationPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authReady, setAuthReady] = useState(false);
  const [profile, setProfile] = useState<TaxProfile | null>(null);
  const [documents, setDocuments] = useState<TaxDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    hydrate();
    setAuthReady(true);
  }, [hydrate]);

  const load = useCallback(async () => {
    const [profileResponse, documentsResponse] = await Promise.all([taxProfileAPI.getCurrentUser(), documentsAPI.list()]);
    setProfile(profileResponse.data);
    setDocuments(documentsResponse.data || []);
    if (!getProfileCompletion(profileResponse.data).minimumReady) setNeedsProfile(true);
  }, []);

  useEffect(() => {
    if (!authReady) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    void load().catch((loadError: any) => setError(loadError?.response?.data?.detail || 'TaxWise could not load information for reconciliation.')).finally(() => setLoading(false));
  }, [authReady, isAuthenticated, load, router]);

  const rows: ReconciliationRow[] = (() => {
    if (!profile) return [];
    const sourceCandidates = (field: string) => ({
      form_16: readCandidate(documents, 'form_16', field),
      ais_tis: readCandidate(documents, 'ais_tis', field),
      form_26as: readCandidate(documents, 'form_26as', field),
    });
    const salarySources = sourceCandidates('salary_income');
    const tdsSources = sourceCandidates('tds');
    const interestSources = sourceCandidates('other_income_interest');
    const totals = {
      salary: profile.salary_income.reduce((sum, item) => sum + Number(item.gross_salary || 0), 0),
      tds: profile.taxes_paid.some((item) => item.tax_type === 'tds')
        ? profile.taxes_paid.filter((item) => item.tax_type === 'tds').reduce((sum, item) => sum + Number(item.amount || 0), 0)
        : profile.salary_income.reduce((sum, item) => sum + Number(item.tds || 0), 0),
      interest: profile.other_income.filter((item) => item.income_type === 'interest').reduce((sum, item) => sum + Number(item.amount || 0), 0),
    };
    const createRow = (key: RowKey, label: string, field: string, sources: typeof salarySources): ReconciliationRow => {
      const mapped: ReconciliationRow['candidates'] = {};
      const values: ReconciliationRow = {
        key,
        label,
        profile: totals[key] > 0 || (key === 'salary' && profile.salary_income.length > 0) || (key === 'tds' && profile.taxes_paid.some((item) => item.tax_type === 'tds')) || (key === 'interest' && profile.other_income.some((item) => item.income_type === 'interest')) ? totals[key] : undefined,
        documentPending: false,
        candidates: mapped,
      };
      for (const [source, data] of Object.entries(sources) as Array<[Source, ReturnType<typeof readCandidate>]>) {
        if (!data) continue;
        mapped[source] = data.candidate;
        values[source === 'form_16' ? 'form16' : source === 'ais_tis' ? 'ais' : 'form26as'] = toNumber(data.candidate.value);
        if (!['CONFIRMED', 'REJECTED'].includes(data.document.status)) values.documentPending = true;
      }
      return values;
    };
    return [
      createRow('salary', 'Salary', 'salary_income', salarySources),
      createRow('tds', 'TDS', 'tds', tdsSources),
      createRow('interest', 'Interest income', 'other_income_interest', interestSources),
    ];
  })();

  const statusFor = (row: ReconciliationRow) => {
    const values = [row.form16, row.ais, row.form26as, row.profile].filter((value): value is number => value !== undefined);
    const firstValue = values[0];
    if (firstValue !== undefined && values.slice(1).some((value) => Math.abs(value - firstValue) > 0.01)) return { label: '✕ CONFLICT', className: 'bg-red-50 text-red-800' };
    if (row.documentPending || values.length < 2) return { label: '⚠ NEEDS REVIEW', className: 'bg-amber-50 text-amber-800' };
    return { label: '✓ MATCHED', className: 'bg-[#ECFDF5] text-[#047857]' };
  };

  const useDocumentValue = async (row: ReconciliationRow, source: Source) => {
    if (!profile) return;
    const candidate = row.candidates[source];
    const amount = candidate ? toNumber(candidate.value) : undefined;
    if (amount === undefined) return;
    const updated = JSON.parse(JSON.stringify(profile)) as TaxProfile;
    if (row.key === 'salary') {
      const salaryEntry = updated.salary_income[0];
      if (salaryEntry) salaryEntry.gross_salary = amount;
      else {
        const employer = row.candidates[source]?.field === 'salary_income'
          ? documents.find((item) => item.document_type === source)?.processing_result?.candidates?.find((item) => item.field === 'employer_name')?.value
          : undefined;
        if (!employer) {
          setNotice('Add an employer name in your profile before selecting this salary value.');
          return;
        }
        updated.salary_income = [{ employer_name: employer, gross_salary: amount, standard_deduction: 0, professional_tax: 0, tds: 0 }];
      }
    } else if (row.key === 'tds') {
      updated.taxes_paid = [
        ...updated.taxes_paid.filter((item) => item.tax_type !== 'tds'),
        { tax_type: 'tds', amount },
      ];
      const salaryEntry = updated.salary_income[0];
      if (salaryEntry) salaryEntry.tds = amount;
    } else {
      const interest = updated.other_income.find((item) => item.income_type === 'interest');
      if (interest) interest.amount = amount;
      else updated.other_income = [...updated.other_income, { income_type: 'interest', description: 'Bank interest', amount, tds: 0 }];
    }
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const response = await taxProfileAPI.update(updated.id || '', updated);
      setProfile(response.data);
      setNotice(`The ${row.label.toLowerCase()} value was updated from ${source.replace(/_/g, ' ').toUpperCase()}.`);
    } catch (saveError: any) {
      setError(saveError?.response?.data?.detail || 'Could not save the selected value. Review it manually in your Tax Profile.');
    } finally {
      setSaving(false);
    }
  };

  if (!authReady || !isAuthenticated || loading) return <main className="min-h-screen bg-[#F8FAFC] p-8 text-[#475569]">Loading reconciliation…</main>;

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Reconciliation</p><h1 className="mt-2 text-3xl font-bold">Tax Information Reconciliation</h1><p className="mt-2 text-sm text-[#64748B]">Compare values actually extracted from uploaded documents with your saved Tax Profile. Conflicts are never resolved automatically.</p></div>
          <div className="flex gap-2"><Link href="/dashboard" className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold">← Back</Link><Link href="/dashboard" className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Dashboard</Link></div>
        </header>
        {error && <p role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
        {notice && <p role="status" className="mb-4 rounded-xl border border-[#A7F3D0] bg-[#ECFDF5] p-4 text-sm text-[#065F46]">{notice}</p>}
        {needsProfile ? <section className="card p-6"><p>Complete your profile before reconciliation can compare saved tax information.</p><Link href="/tax-profile" className="mt-4 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Complete Profile</Link></section> : (
          <section className="card overflow-hidden p-4 sm:p-6">
            <div className="mb-4 flex flex-wrap gap-2 text-xs font-semibold text-[#475569]"><span className="chip">Form 16</span><span className="chip">AIS</span><span className="chip">26AS</span><span className="chip">Tax Profile</span></div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead><tr className="border-b border-[#E2E8F0] text-xs uppercase tracking-wide text-[#64748B]"><th className="py-3 pr-3">Information</th><th className="pr-3">Form 16</th><th className="pr-3">AIS</th><th className="pr-3">26AS</th><th className="pr-3">Profile</th><th>Status</th></tr></thead>
                <tbody>{rows.map((row) => {
                  const status = statusFor(row);
                  const values: Array<[string, Source, number | undefined]> = [['Form 16', 'form_16', row.form16], ['AIS', 'ais_tis', row.ais], ['26AS', 'form_26as', row.form26as]];
                  return <React.Fragment key={row.key}>
                    <tr className="border-b border-[#E2E8F0]"><th className="py-4 pr-3 font-semibold">{row.label}</th><td className="pr-3">{money(row.form16)}</td><td className="pr-3">{money(row.ais)}</td><td className="pr-3">{money(row.form26as)}</td><td className="pr-3">{money(row.profile)}</td><td><span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[10px] font-bold ${status.className}`}>{status.label}</span></td></tr>
                    {status.label.includes('CONFLICT') && <tr className="border-b border-[#E2E8F0]"><td colSpan={6} className="py-3 text-sm text-red-800">Different values were found. Choose which document value to save, or enter a corrected value. No value was applied automatically.</td></tr>}
                    <tr className="border-b border-[#E2E8F0]"><td colSpan={6} className="py-2"><div className="flex flex-wrap gap-2">
                      {values.filter(([, , value]) => value !== undefined).map(([label, source]) => <button key={source} type="button" disabled={saving} onClick={() => void useDocumentValue(row, source)} className="rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-50">Use {label} value</button>)}
                      <Link href="/tax-profile" className="rounded-lg border border-[#CBD5E1] bg-white px-3 py-1.5 text-xs font-semibold">Enter correct value / Edit</Link>
                    </div></td></tr>
                  </React.Fragment>;
                })}</tbody>
              </table>
            </div>
            <p className="mt-4 text-xs text-[#64748B]">A dash means no corresponding value was found. Values from documents that have not been confirmed are marked Needs Review and are not treated as trusted profile data.</p>
          </section>
        )}
      </div>
    </main>
  );
};

export default ReconciliationPage;
