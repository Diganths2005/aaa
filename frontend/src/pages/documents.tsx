import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { documentsAPI, onboardingAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

type DocumentItem = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
};

type Candidate = { field: string; value: string; page?: number };

const DocumentsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [pendingDocument, setPendingDocument] = useState<{ id: string; candidates: Candidate[]; values: Record<string, unknown> } | null>(null);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const load = async () => {
      try {
        const response = await documentsAPI.list();
        setDocuments(response.data || []);
      } catch {
        setMessage('TaxWise could not load your documents right now.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAuthenticated, router]);

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
    } catch {
      setMessage('TaxWise could not complete the document review.');
    }
  };

  if (!isAuthenticated) {
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
          <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
            <span>{processing ? 'Processing...' : 'Upload PDF'}</span>
            <input type="file" accept="application/pdf" className="sr-only" onChange={handleUpload} disabled={processing} />
          </label>
        </header>

        <div className="card p-6">
          <p className="text-base text-[#64748B]">TaxWise extracted this information from your document. Please confirm it before it becomes part of your tax profile.</p>
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
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="chip">{document.status}</span>
                    <button className="rounded-xl border border-border bg-white px-3 py-2 text-xs font-semibold text-[#0F172A]">Review</button>
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
