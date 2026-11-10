import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { documentsAPI, factsAPI, taxProfileAPI } from '@/lib/api';
import { getProfileCompletion } from '@/lib/profile-completion';
import { useAuthStore } from '@/store/auth';

type Candidate = {
  field: string;
  value: string;
  source?: string;
  confidence?: string;
  page?: number;
};

type TaxDocument = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
  processing_result?: {
    candidates?: Candidate[];
    onboarding_values?: Record<string, any>;
    error?: string;
  };
};

const DocumentReviewPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authReady, setAuthReady] = useState(false);
  const [document, setDocument] = useState<TaxDocument | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [previewUrl, setPreviewUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [profileNeedsCompletion, setProfileNeedsCompletion] = useState(false);

  useEffect(() => {
    hydrate();
    setAuthReady(true);
  }, [hydrate]);

  useEffect(() => {
    if (!authReady || !router.isReady) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    if (typeof id !== 'string') return;

    let active = true;
    let objectUrl = '';
    const load = async () => {
      try {
        const response = await documentsAPI.list();
        const found = (response.data || []).find((item: TaxDocument) => item.id === id);
        if (!found) {
          setError('This document could not be found in your account.');
          return;
        }
        if (!active) return;
        setDocument(found);
        setCandidates(found.processing_result?.candidates || []);
        if (found.original_filename.toLowerCase().endsWith('.pdf')) {
          try {
            const content = await documentsAPI.content(id);
            objectUrl = URL.createObjectURL(content.data);
            if (active) setPreviewUrl(objectUrl);
          } catch {
            if (active) setNotice('The document is saved, but its preview is currently unavailable.');
          }
        }
      } catch {
        if (active) setError('TaxWise could not load this document. Please return to the Document Center and try again.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [authReady, id, isAuthenticated, router]);

  const status = document?.status || '';
  const canReview = status === 'REQUIRES_CONFIRMATION' && candidates.length > 0;
  const extracted = useMemo(() => candidates.filter((item) => item.value.trim()), [candidates]);

  const confirm = async (action: 'confirm' | 'reject') => {
    if (!document) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const response = await factsAPI.resolveDocument(document.id, action);
      if (action === 'confirm') {
        try {
          const profile = await taxProfileAPI.getCurrentUser();
          setProfileNeedsCompletion(!getProfileCompletion(profile.data).minimumReady);
        } catch (profileError: any) {
          if (profileError?.response?.status !== 404) throw profileError;
          setProfileNeedsCompletion(true);
        }
      }
      setDocument({ ...document, status: response.data.status });
      setNotice(action === 'confirm'
        ? response.data.conflicts?.length
          ? 'Non-conflicting facts were confirmed. Resolve the flagged conflicts in the Tax Profile fact workspace before using them.'
          : 'Your confirmed facts were projected into your Tax Profile for existing calculations and return preparation.'
        : 'These extracted facts were rejected and were not added to your Tax Profile.');
    } catch (reviewError: any) {
      const detail = reviewError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'TaxWise could not complete the document review. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!authReady || !isAuthenticated || loading) {
    return <main className="min-h-screen bg-[#F8FAFC] p-8 text-[#475569]">Loading document review…</main>;
  }

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Document review</p><h1 className="mt-2 text-3xl font-bold">{document?.original_filename || 'Review document'}</h1><p className="mt-1 text-sm text-[#64748B]">{document?.document_type.replace(/_/g, ' ') || 'Tax document'} · {status.replace(/_/g, ' ')}</p></div>
          <div className="flex gap-2"><Link href="/documents" className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold">← Back to Documents</Link><Link href="/dashboard" className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Dashboard</Link></div>
        </header>

        {error && <p className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert">{error}</p>}
        {notice && <p className="mb-5 rounded-xl border border-[#A7F3D0] bg-[#ECFDF5] p-4 text-sm text-[#065F46]" role="status">{notice}</p>}
        {document?.processing_result?.error && <p className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">Processing error: {document.processing_result.error}</p>}

        <div className="grid gap-5 lg:grid-cols-2">
          <section className="card min-h-[520px] p-4" aria-label="Document preview">
            <h2 className="mb-3 text-lg font-semibold">Original document</h2>
            {previewUrl ? (
              <iframe title={`Preview of ${document?.original_filename}`} src={previewUrl} className="h-[640px] w-full rounded-xl border border-[#E2E8F0]" />
            ) : document?.original_filename.toLowerCase().endsWith('.pdf') ? (
              <div className="flex h-[460px] items-center justify-center rounded-xl border border-dashed border-[#CBD5E1] p-6 text-center text-sm text-[#64748B]">Preview unavailable. You can still review the extracted fields shown here.</div>
            ) : (
              <div className="flex h-[460px] flex-col items-center justify-center rounded-xl border border-dashed border-[#CBD5E1] p-6 text-center">
                <p className="font-semibold">{document?.original_filename}</p><p className="mt-2 text-sm text-[#64748B]">In-browser preview is not available for this spreadsheet format. Review the extracted values on this page.</p>
              </div>
            )}
          </section>

          <section className="card p-5" aria-label="Extracted information">
            <div className="flex items-start justify-between gap-3"><div><h2 className="text-lg font-semibold">Extracted information</h2><p className="mt-1 text-sm text-[#64748B]">Review each value and its evidence. Confirmed facts update your profile projection.</p></div><span className="chip">{document?.status.replace(/_/g, ' ')}</span></div>
            {extracted.length === 0 ? (
              <div className="mt-5 rounded-xl bg-[#F8FAFC] p-5 text-sm text-[#64748B]">No supported fields were extracted from this document. Add the information manually or upload a different file.</div>
            ) : (
              <div className="mt-5 space-y-3">
                {extracted.map((candidate, index) => (
                  <label key={`${candidate.field}-${index}`} className="block rounded-xl border border-[#E2E8F0] p-4">
                    <span className="flex items-center justify-between gap-2 text-sm font-semibold capitalize"><span>{candidate.field.replace(/_/g, ' ')}</span>{candidate.confidence && <span className="text-xs font-normal text-[#64748B]">Confidence: {candidate.confidence}</span>}</span>
                    {candidate.field === 'profile_import'
                      ? <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-[#F8FAFC] p-3 font-mono text-xs">{candidate.value}</pre>
                      : <p className="mt-2 break-all rounded-lg bg-[#F8FAFC] px-3 py-2 text-sm">{candidate.value}</p>}
                    <span className="mt-2 block text-xs text-[#64748B]">{candidate.source || `Extracted from ${document?.document_type.replace(/_/g, ' ')}`}{candidate.page ? ` · Page ${candidate.page}` : ''} · Document-extracted, awaiting confirmation</span>
                  </label>
                ))}
              </div>
            )}

            {canReview && (
              <div className="mt-5 flex flex-wrap gap-3 border-t border-[#E2E8F0] pt-5">
                <button type="button" onClick={() => void confirm('confirm')} disabled={saving} className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving ? 'Saving…' : 'Confirm information'}</button>
                <button type="button" onClick={() => void confirm('reject')} disabled={saving} className="rounded-xl border border-red-200 bg-white px-4 py-2.5 text-sm font-semibold text-red-700 disabled:opacity-50">Reject</button>
                <Link href="/tax-profile" className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold">Edit Tax Profile manually</Link>
              </div>
            )}
            {profileNeedsCompletion && <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Your document values are saved, but more profile information is needed before personalized calculations are available.<Link href="/tax-profile" className="ml-1 font-semibold underline">Complete your Tax Profile</Link></div>}
            {!canReview && document?.status === 'CONFIRMED' && <p className="mt-5 rounded-xl bg-[#ECFDF5] p-4 text-sm text-[#065F46]">This document&apos;s extracted information has been confirmed.</p>}
            {!canReview && document?.status === 'REJECTED' && <p className="mt-5 rounded-xl bg-[#F8FAFC] p-4 text-sm text-[#475569]">This document&apos;s extracted information was rejected and is not part of your confirmed Tax Profile.</p>}
          </section>
        </div>
        <footer className="mt-6 flex flex-wrap gap-4 text-sm font-semibold text-[#047857]"><Link href="/documents">← Back to Documents</Link><Link href="/dashboard">Back to Dashboard</Link></footer>
      </div>
    </main>
  );
};

export default DocumentReviewPage;
