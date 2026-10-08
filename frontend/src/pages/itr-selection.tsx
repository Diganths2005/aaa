import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { itrAPI, taxProfileAPI } from '@/lib/api';
import { getProfileCompletion } from '@/lib/profile-completion';
import { useAuthStore } from '@/store/auth';

type Selection = {
  recommended_itr: string | null;
  eligible: boolean;
  assessment_year: string;
  reasons: string[];
  missing_information: string[];
  unsupported_conditions: string[];
  preparation_supported: boolean;
};

const forms = ['ITR-1', 'ITR-2', 'ITR-3', 'ITR-4'];

const ITRSelectionPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authReady, setAuthReady] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
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
        const response = await itrAPI.selection();
        if (active) setSelection(response.data);
      } catch (loadError: any) {
        if (active) setError(loadError?.response?.data?.detail || 'ITR eligibility is unavailable right now.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [authReady, isAuthenticated, router]);

  if (!authReady || !isAuthenticated || loading) return <main className="min-h-screen bg-[#F8FAFC] p-8 text-[#475569]">Checking ITR readiness…</main>;

  const startable = Boolean(selection?.recommended_itr && selection.eligible && selection.preparation_supported);

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">ITR preparation</p><h1 className="mt-2 text-3xl font-bold">Which ITR should you file?</h1><p className="mt-2 text-sm text-[#64748B]">Form selection is determined by the backend eligibility service, not by AI.</p></div>
          <div className="flex gap-2"><Link href="/dashboard" className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold">← Back</Link><Link href="/dashboard" className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Dashboard</Link></div>
        </header>
        {needsProfile ? (
          <section className="card p-6"><h2 className="text-xl font-bold">Complete your profile first</h2><p className="mt-2 text-sm text-[#64748B]">ITR selection requires saved identity and income information.</p><Link href="/tax-profile" className="mt-4 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Complete Profile</Link></section>
        ) : error ? <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800">{error}</p> : selection ? (
          <>
            {selection.recommended_itr && <section className="mb-5 rounded-2xl border border-[#A7F3D0] bg-[#ECFDF5] p-5"><p className="text-sm font-semibold text-[#047857]">Backend recommendation · AY {selection.assessment_year}</p><p className="mt-2 text-2xl font-bold">{selection.recommended_itr}</p><p className="mt-2 text-sm text-[#334155]">{selection.reasons.join(' ')}</p></section>}
            <section className="grid gap-4 sm:grid-cols-2">
              {forms.map((form) => {
                const isRecommended = form === selection.recommended_itr;
                const enabled = isRecommended && selection.eligible && selection.preparation_supported;
                const title = isRecommended
                  ? enabled ? 'Eligible and supported' : selection.eligible ? 'Partially supported' : 'Not eligible yet'
                  : 'Not evaluated for this profile';
                const reason = isRecommended
                  ? [...selection.missing_information, ...selection.unsupported_conditions, ...selection.reasons].join(' ') || 'The backend selected this form based on your saved information.'
                  : 'The current backend response selects one deterministic form and does not evaluate this form independently. TaxWise will not enable preparation without that support.';
                return (
                  <article key={form} className={`card p-5 ${isRecommended ? 'border-[#10B981]' : ''}`}>
                    <div className="flex items-center justify-between"><h2 className="text-xl font-bold">{form}</h2><span className={`rounded-full px-3 py-1 text-xs font-semibold ${enabled ? 'bg-[#ECFDF5] text-[#047857]' : isRecommended ? 'bg-amber-50 text-amber-800' : 'bg-[#F1F5F9] text-[#475569]'}`}>{enabled ? '✓ Eligible' : isRecommended && selection.eligible ? '⚠ Partially Supported' : isRecommended ? '✕ Not Eligible' : '— Not evaluated'}</span></div>
                    <p className="mt-3 text-sm font-medium text-[#334155]">{title}</p><p className="mt-2 text-sm leading-6 text-[#64748B]">{reason}</p>
                    {enabled && <Link href="/itr-preview" className="mt-5 inline-flex rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Start ITR Preparation</Link>}
                  </article>
                );
              })}
            </section>
          </>
        ) : <p className="card p-6">No ITR selection was returned.</p>}
      </div>
    </main>
  );
};

export default ITRSelectionPage;
