import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { documentsAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';

type DocumentType =
  | 'form_16'
  | 'form_26as'
  | 'ais_tis'
  | 'bank_statement'
  | 'investment_statement'
  | 'insurance'
  | 'capital_gains'
  | 'other';

type Candidate = { field: string; value: string; source?: string; confidence?: string; page?: number };
type DocumentItem = {
  id: string;
  document_type: string;
  original_filename: string;
  status: string;
  created_at?: string;
  processing_result?: { candidates?: Candidate[]; error?: string };
};

const documentCategories: Array<{ type: DocumentType; title: string; description: string }> = [
  { type: 'form_16', title: 'Form 16', description: 'Salary certificates and employer tax information' },
  { type: 'other', title: 'Salary Slip', description: 'Monthly salary documents' },
  { type: 'form_26as', title: 'Form 26AS', description: 'Tax credit information' },
  { type: 'ais_tis', title: 'AIS', description: 'Annual Information Statement' },
  { type: 'bank_statement', title: 'Bank Statement', description: 'Interest and financial information' },
  { type: 'capital_gains', title: 'Capital Gains', description: 'Broker and investment statements' },
  { type: 'investment_statement', title: 'Investment Proof', description: '80C, 80D, and other deduction documents' },
  { type: 'other', title: 'Other Tax Documents', description: 'Other supporting tax records' },
];

const statusLabel = (status: string) => status.replace(/_/g, ' ').toLowerCase();
const errorText = (error: any) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail === 'DOCUMENT_REQUIRES_OCR'
    ? 'No text was found and OCR could not run on this server. Upload a text-based PDF or enter the information manually.'
    : detail;
  return 'The document could not be processed. Please try again or enter the information manually.';
};

const DocumentsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authHydrated, setAuthHydrated] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeUpload, setActiveUpload] = useState<{ type: DocumentType; name: string; percent: number; phase: 'uploading' | 'processing' } | null>(null);
  const [failure, setFailure] = useState<{ id: string; name: string; type: DocumentType; reason: string } | null>(null);
  const [pageMessage, setPageMessage] = useState('');
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    hydrate();
    setAuthHydrated(true);
  }, [hydrate]);

  const loadDocuments = useCallback(async () => {
    const response = await documentsAPI.list();
    setDocuments(response.data || []);
  }, []);

  useEffect(() => {
    if (!authHydrated) return;
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }
    loadDocuments()
      .catch(() => setPageMessage('TaxWise could not load your documents right now.'))
      .finally(() => setLoading(false));
  }, [authHydrated, isAuthenticated, loadDocuments, router]);

  const processExisting = async (document: DocumentItem, type: DocumentType) => {
    setActiveUpload({ type, name: document.original_filename, percent: 100, phase: 'processing' });
    setFailure(null);
    try {
      const processed = await documentsAPI.process(document.id);
      setDocuments((current) => current.map((item) => item.id === document.id
        ? { ...item, status: processed.data.status, processing_result: { candidates: processed.data.candidates } }
        : item));
      if (processed.data.candidates?.length) {
        await router.push(`/document-review/${document.id}`);
      } else {
        setPageMessage('Document processing finished, but no supported tax fields were extracted.');
      }
    } catch (error: any) {
      const reason = errorText(error);
      setFailure({ id: document.id, name: document.original_filename, type, reason });
      setDocuments((current) => current.map((item) => item.id === document.id ? { ...item, status: 'FAILED' } : item));
    } finally {
      setActiveUpload(null);
    }
  };

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>, type: DocumentType) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setPageMessage('');
    setFailure(null);
    setActiveUpload({ type, name: file.name, percent: 0, phase: 'uploading' });
    let uploadedDocument: DocumentItem | null = null;

    try {
      const uploaded = await documentsAPI.upload(file, '2026-27', type, (percent) => {
        setActiveUpload((current) => current ? { ...current, percent } : current);
      });
      uploadedDocument = uploaded.data;
      setDocuments((current) => [uploadedDocument as DocumentItem, ...current]);
      setActiveUpload({ type, name: file.name, percent: 100, phase: 'processing' });
      const processed = await documentsAPI.process(uploaded.data.id);
      setDocuments((current) => current.map((item) => item.id === uploaded.data.id
        ? { ...item, status: processed.data.status, processing_result: { candidates: processed.data.candidates } }
        : item));
      if (processed.data.candidates?.length) {
        await router.push(`/document-review/${uploaded.data.id}`);
      } else {
        setPageMessage(`${file.name} was processed, but no supported tax fields were extracted. You can enter the details manually.`);
      }
    } catch (error: any) {
      const reason = errorText(error);
      if (uploadedDocument) {
        setDocuments((current) => current.map((item) => item.id === uploadedDocument?.id
          ? { ...item, status: 'FAILED', processing_result: { error: reason } }
          : item));
        setFailure({ id: uploadedDocument.id, name: file.name, type, reason });
      } else {
        setPageMessage(reason);
      }
    } finally {
      setActiveUpload(null);
    }
  };

  const removeDocument = async (id: string) => {
    setDeleting(id);
    setPageMessage('');
    try {
      await documentsAPI.delete(id);
      setDocuments((current) => current.filter((document) => document.id !== id));
      if (failure?.id === id) setFailure(null);
    } catch (error: any) {
      setPageMessage(errorText(error));
    } finally {
      setDeleting(null);
    }
  };

  if (!authHydrated || !isAuthenticated) return null;

  const processedCount = documents.filter((item) => ['PROCESSED', 'REQUIRES_CONFIRMATION', 'CONFIRMED', 'REJECTED'].includes(item.status)).length;
  const reviewCount = documents.filter((item) => item.status === 'REQUIRES_CONFIRMATION').length;
  const errorCount = documents.filter((item) => item.status === 'FAILED').length;

  return (
    <main className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Document center</p>
            <h1 className="mt-2 text-3xl font-bold">Your tax documents</h1>
            <p className="mt-2 text-sm text-[#64748B]">Upload by document type. Extracted information stays unconfirmed until you review it.</p>
          </div>
          <div className="flex gap-3"><Link href="/dashboard" className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-2.5 text-sm font-semibold">← Dashboard</Link><ReturnToDashboard /></div>
        </header>

        <section className="mb-6 grid gap-3 sm:grid-cols-4" aria-label="Document processing summary">
          {[['Uploaded', documents.length], ['Processed', processedCount], ['Review required', reviewCount], ['Errors', errorCount]].map(([label, count]) => (
            <div key={label} className="card p-4"><p className="text-xs font-semibold uppercase tracking-wide text-[#64748B]">{label}</p><p className="mt-2 text-2xl font-bold">{count}</p></div>
          ))}
        </section>

        {pageMessage && <p className="mb-5 rounded-xl border border-[#FECACA] bg-[#FEF2F2] p-4 text-sm text-[#991B1B]" role="alert">{pageMessage}</p>}

        {activeUpload && (
          <section className="mb-6 rounded-2xl border border-[#A7F3D0] bg-white p-5" role="status" aria-live="polite">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><p className="font-semibold">Processing {activeUpload.name}</p><p className="mt-1 text-sm text-[#64748B]">{activeUpload.phase === 'uploading' ? 'Uploading document…' : 'Reading document and extracting supported fields…'}</p></div>
              <span className="text-sm font-semibold text-[#047857]">{activeUpload.phase === 'uploading' ? `${activeUpload.percent}% uploaded` : 'Processing'}</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#E2E8F0]">
              <div className={`h-full rounded-full bg-[#047857] transition-all ${activeUpload.phase === 'processing' ? 'w-full animate-pulse' : ''}`} style={activeUpload.phase === 'uploading' ? { width: `${activeUpload.percent}%` } : undefined} />
            </div>
            <ol className="mt-4 grid gap-2 text-xs text-[#475569] sm:grid-cols-3">
              <li>{activeUpload.phase === 'processing' ? '✓' : activeUpload.percent > 0 ? '●' : '○'} Upload</li>
              <li>{activeUpload.phase === 'processing' ? '●' : '○'} Identify and read document</li>
              <li>○ Review and confirm extracted information</li>
            </ol>
          </section>
        )}

        {failure && (
          <section className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-5" role="alert">
            <h2 className="font-semibold text-red-900">Unable to process this document</h2>
            <p className="mt-2 text-sm text-red-800"><strong>{failure.name}</strong> · {failure.reason}</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <button type="button" onClick={() => { const doc = documents.find((item) => item.id === failure.id); if (doc) void processExisting(doc, failure.type); }} className="rounded-xl bg-red-800 px-4 py-2.5 text-sm font-semibold text-white">Try again</button>
              <Link href="/tax-profile" className="rounded-xl border border-red-300 bg-white px-4 py-2.5 text-sm font-semibold text-red-900">Enter information manually</Link>
              <Link href="/dashboard" className="rounded-xl border border-red-300 bg-white px-4 py-2.5 text-sm font-semibold text-red-900">Back to Dashboard</Link>
            </div>
          </section>
        )}

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {documentCategories.map((category) => (
            <article key={category.title} className="card flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div><h2 className="text-lg font-semibold">{category.title}</h2><p className="mt-2 text-sm leading-6 text-[#64748B]">{category.description}</p></div>
                <span aria-hidden="true" className="rounded-xl bg-[#ECFDF5] px-3 py-2 text-xl">📄</span>
              </div>
              <label className={`mt-5 inline-flex cursor-pointer items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold text-white ${activeUpload ? 'cursor-not-allowed bg-[#94A3B8]' : 'bg-[#047857] hover:bg-[#065F46]'}`}>
                Upload {category.title}
                <input type="file" accept="application/pdf,.xlsx,.xlsm" className="sr-only" disabled={!!activeUpload} onChange={(event) => void handleUpload(event, category.type)} />
              </label>
            </article>
          ))}
        </section>

        <section className="mt-8 card p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="text-xl font-bold">Uploaded documents</h2><p className="mt-1 text-sm text-[#64748B]">Open any item requiring confirmation to review the original document and extracted fields.</p></div>
            <Link href="/tax-profile" className="text-sm font-semibold text-[#047857]">Enter information manually →</Link>
          </div>
          {loading ? <p className="mt-5 text-sm text-[#64748B]">Loading your documents…</p> : documents.length === 0 ? (
            <p className="mt-5 rounded-xl border border-dashed border-[#CBD5E1] p-7 text-center text-sm text-[#64748B]">No tax documents have been uploaded yet.</p>
          ) : (
            <div className="mt-5 divide-y divide-[#E2E8F0]">
              {documents.map((document) => (
                <div key={document.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                  <div><p className="font-semibold">{document.original_filename}</p><p className="mt-1 text-xs text-[#64748B]">{document.document_type.replace(/_/g, ' ')} · {statusLabel(document.status)}</p></div>
                  <div className="flex flex-wrap gap-2">
                    {document.status === 'REQUIRES_CONFIRMATION' && <Link href={`/document-review/${document.id}`} className="rounded-lg bg-[#047857] px-3 py-2 text-xs font-semibold text-white">Review information</Link>}
                    {document.status === 'FAILED' && <button type="button" onClick={() => void processExisting(document, (document.document_type as DocumentType) || 'other')} className="rounded-lg border border-[#CBD5E1] bg-white px-3 py-2 text-xs font-semibold">Try again</button>}
                    <button type="button" onClick={() => void removeDocument(document.id)} disabled={deleting === document.id} className="rounded-lg border border-red-200 bg-white px-3 py-2 text-xs font-semibold text-red-700 disabled:opacity-50">{deleting === document.id ? 'Removing…' : 'Remove'}</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
        <footer className="mt-6 flex flex-wrap gap-3"><Link href="/documents" className="text-sm font-semibold text-[#047857]">← Back to Documents</Link><Link href="/dashboard" className="text-sm font-semibold text-[#047857]">Dashboard</Link></footer>
      </div>
    </main>
  );
};

export default DocumentsPage;
