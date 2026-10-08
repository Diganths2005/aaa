import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { documentsAPI, onboardingAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { getProfileCompletion } from '@/lib/profile-completion';
import ReturnToDashboard from '@/components/ReturnToDashboard';

const OnboardingPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [choice, setChoice] = useState<'documents' | 'manual' | 'both' | null>(null);
  const [message, setMessage] = useState('');
  const [uploading, setUploading] = useState(false);
  const [completion, setCompletion] = useState({ percent: 0, missing: [] as string[], minimumReady: false });

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const loadOnboarding = async () => {
      try {
        const response = await taxProfileAPI.getCurrentUser();
        const documentResponse = await documentsAPI.list();
        const status = getProfileCompletion(response.data, (documentResponse.data || []).length);
        setCompletion(status);
        if (status.minimumReady) {
          router.replace('/dashboard');
          return;
        }
      } catch (error: any) {
        if (error.response?.status !== 404) {
          setMessage('We could not load your saved profile. You can still choose a setup method below.');
        }
      } finally {
        setLoading(false);
      }
    };

    loadOnboarding();
  }, [isAuthenticated, router]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setMessage('Processing your document and preparing your profile…');

    try {
      const uploaded = await documentsAPI.upload(file, '2026-27');
      const processed = await documentsAPI.process(uploaded.data.id);
      if (processed.data.candidates?.length) {
        await router.push(`/document-review/${uploaded.data.id}`);
        return;
      }
      setMessage('The document was processed, but no supported fields were extracted. Continue by entering information manually or upload another document.');
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      setMessage(typeof detail === 'string' && detail !== 'DOCUMENT_REQUIRES_OCR'
        ? detail
        : detail === 'DOCUMENT_REQUIRES_OCR'
          ? 'No text was found and OCR could not run on this server. Upload a text-based PDF or enter the details manually.'
          : 'We could not extract your document. You can still continue by entering information manually.');
      setUploading(false);
    }
  };

  if (!isAuthenticated || loading) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-10 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl rounded-[28px] border border-[#E2E8F0] bg-white p-6 shadow-soft sm:p-10">
        <div className="flex items-start justify-between gap-4">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TaxWise onboarding</p>
          {completion.minimumReady && <ReturnToDashboard />}
        </div>
        <h1 className="mt-4 text-3xl font-bold text-[#0F172A] sm:text-4xl">Welcome to TaxWise</h1>
        <p className="mt-3 max-w-2xl text-base text-[#64748B]">
          Let&apos;s build your Tax Profile. How would you like to provide your tax information?
        </p>

        <section className="mt-8 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-5" aria-labelledby="completion-heading">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 id="completion-heading" className="font-semibold text-[#0F172A]">Profile completion</h2>
              <p className="mt-1 text-sm text-[#64748B]">{completion.percent}% complete</p>
            </div>
            <span className="text-sm font-semibold text-[#047857]">{completion.minimumReady ? 'Ready for tax calculations' : 'Setup in progress'}</span>
          </div>
          <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-[#E2E8F0]" role="progressbar" aria-valuenow={completion.percent} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full rounded-full bg-[#047857] transition-all" style={{ width: `${completion.percent}%` }} />
          </div>
          {completion.missing.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-[#334155]">Information not yet provided:</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-[#64748B]">
                {completion.missing.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          )}
        </section>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <button
            type="button"
            onClick={() => setChoice('documents')}
            className={`rounded-2xl border p-6 text-left transition ${
              choice === 'documents' ? 'border-[#10B981] bg-[#ECFDF5]' : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#10B981]'
            }`}
          >
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-[#D1FAE5] text-xl">📄</div>
            <p className="text-xl font-semibold text-[#0F172A]">Upload Documents</p>
            <p className="mt-2 text-sm text-[#475569]">Upload a PDF or Excel workbook. Extraction recognizes known labels; results are candidates for your review.</p>
          </button>

          <button
            type="button"
            onClick={() => { setChoice('manual'); void router.push('/tax-profile'); }}
            className={`rounded-2xl border p-6 text-left transition ${choice === 'manual' ? 'border-[#10B981] bg-[#ECFDF5]' : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#10B981]'}`}
          >
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-[#E0F2FE] text-xl">✍️</div>
            <p className="text-xl font-semibold text-[#0F172A]">Enter Information Manually</p>
            <p className="mt-2 text-sm text-[#475569]">Complete your profile step by step with the guided profile editor.</p>
          </button>

          <button
            type="button"
            onClick={() => setChoice('both')}
            className={`rounded-2xl border p-6 text-left transition ${choice === 'both' ? 'border-[#10B981] bg-[#ECFDF5]' : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#10B981]'}`}
          >
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-[#FEF3C7] text-xl">↔️</div>
            <p className="text-xl font-semibold text-[#0F172A]">Do Both</p>
            <p className="mt-2 text-sm text-[#475569]">Upload supporting documents, then review and fill any information that is still missing.</p>
          </button>
        </div>

        <div className="mt-8 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-4">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Supported extracted fields</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[#475569]">
            {['Name and PAN', 'Date of birth and assessment year', 'Employer and gross salary', 'TDS and advance tax', '80C, 80D, 80CCD(1B)', 'Bank interest and dividends', 'Professional receipts and net income'].map((item) => (
              <span key={item} className="rounded-full border border-[#E2E8F0] bg-white px-2.5 py-1.5">{item}</span>
            ))}
          </div>
        </div>

        {choice === 'documents' && (
          <div className="mt-8 rounded-2xl border border-dashed border-[#94A3B8] bg-[#F8FAFC] p-6">
            <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white hover:bg-[#065F46]">
              <span>{uploading ? 'Reading document...' : 'Select PDF or Excel'}</span>
              <input type="file" accept="application/pdf,.xlsx,.xlsm" className="sr-only" onChange={handleUpload} disabled={uploading} />
            </label>

            <p className="mt-4 text-sm text-[#475569]">
              TaxWise will review the file, extract likely values, and take you to a review step before your tax profile is confirmed.
            </p>
          </div>
        )}

        {choice === 'both' && (
          <div className="mt-8 flex flex-wrap gap-3 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-5">
            <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white hover:bg-[#065F46]">
              <span>{uploading ? 'Processing document…' : 'Upload a document first'}</span>
              <input type="file" accept="application/pdf,.xlsx,.xlsm" className="sr-only" onChange={handleUpload} disabled={uploading} />
            </label>
            <button type="button" onClick={() => router.push('/tax-profile')} className="rounded-xl border border-[#CBD5E1] bg-white px-4 py-3 text-sm font-semibold text-[#334155]">
              Continue with manual information
            </button>
          </div>
        )}

        {message && <div className="mt-6 rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] p-4 text-sm text-[#047857]">{message}</div>}

        <p className="mt-8 border-t border-[#E2E8F0] pt-6 text-sm text-[#64748B]">
          Personalized tax calculations stay locked until your identity and at least one income source are provided. Extracted document values are not used until you review and confirm them.
        </p>
      </div>
    </div>
  );
};

export default OnboardingPage;