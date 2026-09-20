import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { documentsAPI, onboardingAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

const OnboardingPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [choice, setChoice] = useState<'documents' | 'manual' | null>(null);
  const [message, setMessage] = useState('');
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const checkProfile = async () => {
      try {
        await taxProfileAPI.getCurrentUser();
        router.push('/dashboard');
      } catch {
        setLoading(false);
      }
    };

    checkProfile();
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
        await onboardingAPI.documentCandidate(processed.data.onboarding_values || {});
      }
      router.push('/tax-profile');
    } catch (error: any) {
      const detail = error.response?.data?.detail;
      setMessage(
        detail === 'DOCUMENT_REQUIRES_OCR'
          ? 'This PDF appears to be scanned. Please continue by entering the details manually.'
          : 'We could not extract your document yet. You can still continue by entering it manually.'
      );
      setUploading(false);
    }
  };

  if (!isAuthenticated || loading) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-10 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl rounded-[28px] border border-[#E2E8F0] bg-white p-6 shadow-soft sm:p-10">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TaxWise onboarding</p>
        <h1 className="mt-4 text-3xl font-bold text-[#0F172A] sm:text-4xl">How would you like to provide your tax information?</h1>
        <p className="mt-3 max-w-2xl text-base text-[#64748B]">
          Choose the easiest path to build your profile and continue to your personalized dashboard.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <button
            type="button"
            onClick={() => setChoice('documents')}
            className={`rounded-2xl border p-6 text-left transition ${
              choice === 'documents' ? 'border-[#10B981] bg-[#ECFDF5]' : 'border-[#E2E8F0] bg-[#F8FAFC] hover:border-[#10B981]'
            }`}
          >
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-[#D1FAE5] text-xl">📄</div>
            <p className="text-xl font-semibold text-[#0F172A]">Upload documents</p>
            <p className="mt-2 text-sm text-[#475569]">Use your PDF or tax forms to speed up profile creation.</p>
          </button>

          <button
            type="button"
            onClick={() => router.push('/tax-profile')}
            className="rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-6 text-left transition hover:border-[#10B981]"
          >
            <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-[#E0F2FE] text-xl">✍️</div>
            <p className="text-xl font-semibold text-[#0F172A]">Enter manually</p>
            <p className="mt-2 text-sm text-[#475569]">Complete your profile step by step with the guided assistant.</p>
          </button>
        </div>

        {choice === 'documents' && (
          <div className="mt-8 rounded-2xl border border-dashed border-[#94A3B8] bg-[#F8FAFC] p-6">
            <label className="inline-flex cursor-pointer items-center justify-center rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white hover:bg-[#065F46]">
              <span>{uploading ? 'Processing...' : 'Select a PDF'}</span>
              <input type="file" accept="application/pdf" className="sr-only" onChange={handleUpload} disabled={uploading} />
            </label>

            <p className="mt-4 text-sm text-[#475569]">
              TaxWise will extract information and take you to the profile builder for review.
            </p>
          </div>
        )}

        {message && <div className="mt-6 rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] p-4 text-sm text-[#047857]">{message}</div>}

        <div className="mt-8 flex items-center justify-between gap-3 border-t border-[#E2E8F0] pt-6">
          <button type="button" onClick={() => router.push('/login')} className="rounded-xl border border-[#CBD5E1] px-4 py-2.5 text-sm font-medium text-[#0F172A]">
            Back to login
          </button>
          <button type="button" onClick={() => router.push('/tax-profile')} className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]">
            Start manual profile
          </button>
        </div>
      </div>
    </div>
  );
};

export default OnboardingPage;