import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { documentsAPI, readinessAPI, taxProfileAPI } from '@/lib/api';
import ReturnToDashboard from '@/components/ReturnToDashboard';
import { useAuthStore } from '@/store/auth';

type ReadinessItem = {
  key: string;
  label: string;
  section: string;
  required: boolean;
  status: 'complete' | 'missing' | 'needs_confirmation';
  value?: unknown;
  source?: string | null;
  page?: number | null;
  confidence?: string | null;
};

type Readiness = {
  itr: string;
  ready: boolean;
  completion_percentage: number;
  total_required: number;
  complete_required: number;
  missing: ReadinessItem[];
  needs_confirmation: ReadinessItem[];
  sections: Array<{ name: string; total: number; complete: number; missing: number; review: number }>;
};

const TaxProfilePage = () => {
  const { isAuthenticated, hydrate } = useAuthStore();
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const load = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    setError('');
    try {
      const [profileResponse, readinessResponse] = await Promise.all([
        taxProfileAPI.getCurrentUser(),
        readinessAPI.itr2(),
      ]);
      setProfile(profileResponse.data);
      setReadiness(readinessResponse.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not load your Tax Profile.');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    void load();
  }, [load]);

  const upload = async (file: File) => {
    setUploading(true);
    setError('');
    setNotice('');
    try {
      const uploaded = await documentsAPI.upload(file, profile?.assessment_year || '2026-27', 'other');
      await documentsAPI.process(uploaded.data.id);
      setNotice('Document processed. Review the extracted facts before confirming them.');
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Document processing failed. Please try another file.');
    } finally {
      setUploading(false);
    }
  };

  if (!isAuthenticated) {
    return <main className="min-h-screen bg-slate-50 p-8 text-slate-600">Please sign in to continue.</main>;
  }

  return (
    <main className="min-h-screen bg-[#F8FAFC] text-[#0F172A]">
      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8">
        <header className="mb-7 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">TaxWise</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">Tax Profile & ITR readiness</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              TaxWise determines what is actually required for your return. It does not count unrelated empty profile fields.
            </p>
          </div>
          <ReturnToDashboard />
        </header>

        {error && <p className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
        {notice && <p className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}

        <section className="mb-6 grid gap-5 lg:grid-cols-[1fr_300px]">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-slate-500">Preparation readiness</p>
                <p className="mt-1 text-4xl font-bold">{readiness?.completion_percentage ?? 0}%</p>
                <p className="mt-1 text-sm text-slate-500">
                  {readiness ? `${readiness.complete_required} of ${readiness.total_required} required facts complete` : 'Calculating…'}
                </p>
              </div>
              <div className={`rounded-xl px-4 py-3 text-sm font-semibold ${readiness?.ready ? 'bg-emerald-50 text-emerald-800' : 'bg-amber-50 text-amber-800'}`}>
                {readiness?.ready ? '✓ Ready for ITR-2 preparation' : 'Needs information or review'}
              </div>
            </div>
            <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-emerald-600 transition-all" style={{ width: `${readiness?.completion_percentage ?? 0}%` }} />
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm font-semibold text-slate-500">Current return</p>
            <p className="mt-2 text-2xl font-bold">{readiness?.itr || 'ITR-2'}</p>
            <p className="mt-2 text-sm text-slate-500">AY {profile?.assessment_year || '2026-27'}</p>
            <Link href="/taxpayer-profile" className="mt-5 inline-flex rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white">
              Edit Tax Profile
            </Link>
          </div>
        </section>

        <section className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Upload tax documents</h2>
              <p className="mt-1 text-sm text-slate-500">
                Upload Form 16, AIS, bank/investment statements or your ITR-2 test PDF. TaxWise extracts facts first; nothing is silently added to your profile.
              </p>
            </div>
            <label className="cursor-pointer rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800">
              {uploading ? 'Processing…' : 'Upload PDF / Excel'}
              <input
                type="file"
                accept="application/pdf,.xlsx,.xlsm"
                className="hidden"
                disabled={uploading}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void upload(file);
                  event.currentTarget.value = '';
                }}
              />
            </label>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-2">
          {(readiness?.sections || []).map((section) => (
            <div key={section.name} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">{section.name}</h2>
                <span className={`text-sm font-semibold ${section.missing || section.review ? 'text-amber-700' : 'text-emerald-700'}`}>
                  {section.complete}/{section.total}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                {section.missing ? `${section.missing} missing` : 'No missing required facts'}
                {section.review ? ` · ${section.review} awaiting confirmation` : ''}
              </p>
            </div>
          ))}
        </section>

        {(readiness?.missing?.length || readiness?.needs_confirmation?.length) ? (
          <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold">What TaxWise still needs</h2>
            <div className="mt-4 space-y-3">
              {readiness.missing.map((item) => (
                <div key={item.key} className="rounded-xl border border-red-100 bg-red-50 p-4">
                  <p className="font-semibold text-red-900">{item.label}</p>
                  <p className="mt-1 text-xs text-red-700">{item.section} · Missing</p>
                </div>
              ))}
              {readiness.needs_confirmation.map((item) => (
                <div key={item.key} className="rounded-xl border border-amber-100 bg-amber-50 p-4">
                  <p className="font-semibold text-amber-900">{item.label}</p>
                  <p className="mt-1 text-xs text-amber-700">{item.section} · Review required{item.source ? ` · ${item.source}` : ''}{item.page ? ` · Page ${item.page}` : ''}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {loading && <p className="mt-6 text-sm text-slate-500">Loading readiness…</p>}
      </div>
    </main>
  );
};

export default TaxProfilePage;
