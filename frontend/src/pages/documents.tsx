import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { documentsAPI, onboardingAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';

type DocumentItem = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
  processing_result?: { candidates?: Candidate[]; onboarding_values?: Record<string, unknown> };
};

type Candidate = { field: string; value: string; page?: number };

const DocumentsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authHydrated, setAuthHydrated] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [pendingDocument, setPendingDocument] = useState<{ id: string; candidates: Candidate[]; values: Record<string, unknown> } | null>(null);
  const [processing, setProcessing] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

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

    const load = async () => {
      try {
        const response = await documentsAPI.list();
        const loadedDocuments = response.data || [];
        setDocuments(loadedDocuments);
        const pending = loadedDocuments.find(
          (document: DocumentItem) => document.status === 'REQUIRES_CONFIRMATION' && document.processing_result?.candidates?.length
        );
        if (pending?.processing_result?.candidates) {
          setPendingDocument({
            id: pending.id,
            candidates: pending.processing_result.candidates,
            values: pending.processing_result.onboarding_values || {},
          });
        }
      } catch {
        setMessage('TaxWise could not load your documents right now.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [authHydrated, isAuthenticated, router]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    event.target.value = '';

    try {
      setProcessing(true);
      const uploaded = await documentsAPI.upload(file, '2026-27');
      const processed = await documentsAPI.process(uploaded.data.id);
      setDocuments((current) => [{ ...uploaded.data, status: processed.data.status }, ...current]);
      if (processed.data.candidates?.length) {
        setPendingDocument({ id: uploaded.data.id, candidates: processed.data.candidates, values: processed.data.onboarding_values || {} });
      }
      setMessage(processed.data.candidates?.length ? 'TaxWise found these values. Review and confirm them before they update your Tax Profile.' : 'The document was processed, but no supported tax fields were found.');
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      setMessage(detail === 'DOCUMENT_REQUIRES_OCR' ? 'This PDF is scanned and needs OCR, which is not available yet.' : 'TaxWise could not process this PDF. No profile data was changed.');
    } finally {
      setProcessing(false);
    }
  };

  const confirmDocument = async (action: 'confirm' | 'reject') => {
    if (!pendingDocument) return;
    try {
      await onboardingAPI.documentCandidate(pendingDocument.values);
      await onboardingAPI.confirm(action);
      setMessage(action === 'confirm' ? 'Confirmed values were added to your Tax Profile.' : 'Document values were rejected. Your Tax Profile was not changed.');
      setPendingDocument(null);
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      setMessage(detail ? `TaxWise could not complete the document review: ${detail}` : 'TaxWise could not complete the document review.');
    }
  };

  const deleteDocument = async (documentId: string) => {
    setDeleting(documentId);
    try {
      await documentsAPI.delete(documentId);
      setDocuments((current) => current.filter((document) => document.id !== documentId));
      if (pendingDocument?.id === documentId) setPendingDocument(null);
      setMessage('Document removed.');
    } catch {
      setMessage('TaxWise could not remove this document.');
    } finally {
      setDeleting(null);
    }
  };

  if (!authHydrated || !isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Documents</p>
            <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Document intelligence</h1>
          </div>
          <div className="flex flex-wrap gap-3">
            <ReturnToDashboard />
            <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
              <span>{processing ? 'Processing...' : 'Upload PDF or Excel'}</span>
              <input type="file" accept="application/pdf,.xlsx,.xlsm" className="sr-only" onChange={handleUpload} disabled={processing} />
            </label>
          </div>
        </header>

        <div className="card p-6">
          <p className="text-base text-[#64748B]">TaxWise extracted this information from your document. Please confirm it before it becomes part of your tax profile.</p>
        </div>

        <div className="mt-6 card p-6">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Excel templates</p>
          <p className="mt-2 text-sm text-[#64748B]">Download a template, replace the sample values, save it, and upload it here.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            {(['ITR1', 'ITR2', 'ITR3'] as const).map((form) => (
              <a key={form} href={`/templates/TaxWise_${form}_Template.xlsx`} download className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold text-[#334155] hover:bg-[#F1F5F9]">
                Download {form} template
              </a>
            ))}
          </div>
        </div>

        {message && <div className="mt-6 rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] p-4 text-sm text-[#047857]">{message}</div>}

        {pendingDocument && (
          <div className="mt-6 rounded-2xl border border-[#F59E0B] bg-[#FFFBEB] p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#92400E]">Review extracted information</p>
            <div className="mt-4 space-y-2 text-sm text-[#451A03]">
              {pendingDocument.candidates.map((candidate, index) => <div key={`${candidate.field}-${index}`} className="flex justify-between gap-4 border-b border-[#FDE68A] pb-2"><span>{candidate.field}</span><span className="font-semibold">{candidate.value}</span></div>)}
            </div>
            <div className="mt-5 flex gap-3">
              <button type="button" onClick={() => confirmDocument('confirm')} className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white">Confirm and add</button>
              <button type="button" onClick={() => confirmDocument('reject')} className="rounded-xl border border-[#92400E] px-4 py-2.5 text-sm font-semibold text-[#92400E]">Reject</button>
            </div>
          </div>
        )}

        <div className="mt-8 card p-6">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Uploaded documents</p>
          {loading ? (
            <div className="mt-5 text-sm text-[#64748B]">Loading documents…</div>
          ) : documents.length === 0 ? (
            <div className="mt-5 rounded-2xl border border-dashed border-border bg-[#F8FAFC] p-8 text-center text-sm text-[#64748B]">No documents uploaded yet.</div>
          ) : (
            <div className="mt-5 space-y-3">
              {documents.map((document) => (
                <div key={document.id} className="flex flex-col justify-between gap-3 rounded-2xl border border-border bg-[#F8FAFC] p-4 sm:flex-row sm:items-center">
                  <div>
                    <p className="font-semibold text-[#0F172A]">{document.original_filename}</p>
                    <p className="mt-1 text-sm text-[#64748B]">{document.document_type}</p>
                    {document.processing_result?.candidates?.length ? (
                      <div className="mt-3 grid gap-1 text-xs text-[#475569] sm:grid-cols-2">
                        {document.processing_result.candidates.map((candidate, index) => (
                          <span key={`${candidate.field}-${index}`}><strong>{candidate.field.replace(/_/g, ' ')}:</strong> {candidate.value}</span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="chip">{document.status}</span>
                    <button type="button" onClick={() => deleteDocument(document.id)} disabled={deleting === document.id} className="rounded-xl border border-red-200 bg-white px-3 py-2 text-xs font-semibold text-red-700 disabled:opacity-50">{deleting === document.id ? 'Removing...' : 'Remove'}</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DocumentsPage;
