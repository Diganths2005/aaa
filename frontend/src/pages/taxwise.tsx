import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';
import { chatAPI, taxProfileAPI } from '@/lib/api';
import ReturnToDashboard from '@/components/ReturnToDashboard';

type Message = {
  role: 'user' | 'assistant';
  text: string;
  retryMessage?: string;
  sources?: string[];
  mode?: string;
};

type TaxProfileSummary = {
  salary_income: Array<{ gross_salary: number; tds?: number }>;
  pension_income: Array<{ amount: number; tds?: number }>;
  other_income: Array<{ tds: number }>;
  taxes_paid: Array<{ tax_type: string; amount: number }>;
  deductions: Array<{ section: string; amount: number }>;
  assessment_year: string;
};

const suggestedPrompts = [
  'Why is my tax this high?',
  'Which regime is better for me?',
  'What is my taxable income?',
  'How much TDS is recorded?',
  'What are my rebate and cess amounts?',
  'Which ITR did you recommend for me?',
];

const formatMoney = (value: number) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const TaxWisePage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: 'I’m TaxWise, your personal tax assistant. I can help with Indian income tax, deductions, tax documents, and filing readiness. Ask me about your tax profile or a tax scenario.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<TaxProfileSummary | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    taxProfileAPI.getCurrentUser()
      .then((response) => setProfile(response.data))
      .catch(() => setProfile(null))
      .finally(() => setProfileLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  const handleSend = async (value?: string) => {
    const message = (value ?? input).trim();
    if (!message || loading) return;

    setMessages((current) => [...current, { role: 'user', text: message }]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatAPI.send(message);
      const payload = response.data;
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: payload.answer,
          sources: payload.sources || [],
          mode: payload.mode,
        },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          text: 'TaxWise could not reach the assistant service. Your previous messages are safe. Try the question again.',
          retryMessage: message,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A]">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TaxWise</p>
            <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Your personal tax assistant</h1>
          </div>
          <ReturnToDashboard />
        </header>

        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.6fr]">
          <aside className="card p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">What TaxWise knows</p>
            {profileLoading ? (
              <p className="mt-5 text-sm text-[#64748B]">Loading confirmed profile facts…</p>
            ) : profile ? (
              <dl className="mt-5 space-y-3 text-sm">
                <div><dt className="text-[#64748B]">Salary and pension</dt><dd className="font-medium text-[#0F172A]">{formatMoney(profile.salary_income.reduce((sum, item) => sum + Number(item.gross_salary || 0), 0) + profile.pension_income.reduce((sum, item) => sum + Number(item.amount || 0), 0))}</dd></div>
                <div><dt className="text-[#64748B]">TDS recorded as tax paid</dt><dd className="font-medium text-[#0F172A]">{formatMoney(profile.taxes_paid.filter((item) => item.tax_type === 'tds').reduce((sum, item) => sum + Number(item.amount || 0), 0) || profile.salary_income.reduce((sum, item) => sum + Number(item.tds || 0), 0) + profile.pension_income.reduce((sum, item) => sum + Number(item.tds || 0), 0) + profile.other_income.reduce((sum, item) => sum + Number(item.tds || 0), 0))}</dd></div>
                <div><dt className="text-[#64748B]">Deduction claims in profile</dt><dd className="font-medium text-[#0F172A]">{formatMoney(profile.deductions.reduce((sum, item) => sum + Number(item.amount || 0), 0))} across {profile.deductions.length} claims</dd></div>
                <div><dt className="text-[#64748B]">Assessment year</dt><dd className="font-medium text-[#0F172A]">{profile.assessment_year}</dd></div>
              </dl>
            ) : (
              <p className="mt-5 text-sm text-[#64748B]">No saved Tax Profile was found. Create one to get personal calculation answers.</p>
            )}

            <div className="mt-6">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Suggested prompts</p>
              <div className="mt-4 space-y-2">
                {suggestedPrompts.map((prompt) => (
                  <button key={prompt} onClick={() => handleSend(prompt)} className="w-full rounded-xl border border-border bg-[#F8FAFC] px-3 py-2 text-left text-sm text-[#0F172A] hover:border-[#10B981] hover:bg-[#ECFDF5]">
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <section className="card overflow-hidden">
            <div className="flex h-[620px] flex-col">
              <div className="border-b border-border bg-[#F8FAFC] p-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#064E3B] text-sm font-bold text-white">T</div>
                  <div>
                    <p className="text-sm font-semibold text-[#0F172A]">TaxWise</p>
                    <p className="text-xs text-[#64748B]">AI tax guidance</p>
                  </div>
                </div>
              </div>

              <div className="flex-1 space-y-4 overflow-y-auto p-4">
                {messages.map((message, index) => (
                  <div key={`${message.role}-${index}`} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${message.role === 'user' ? 'bg-[#064E3B] text-white' : 'border border-border bg-[#F8FAFC] text-[#0F172A]'}`}>
                    {message.role === 'assistant' && <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#047857]">{message.mode === 'assistant' ? 'AI explanation' : 'TaxWise explanation'}</p>}
                    <p className="whitespace-pre-wrap text-sm leading-6">{message.text}</p>
                    {message.sources && message.sources.length > 0 && (
                      <details className="mt-3 border-t border-border pt-2 text-xs text-[#64748B]">
                        <summary className="cursor-pointer font-semibold">📚 Sources used</summary>
                        <ul className="mt-2 list-inside list-disc space-y-1">
                          {message.sources.map((source) => <li key={source}>{source}</li>)}
                        </ul>
                      </details>
                    )}
                      {message.retryMessage && (
                        <button
                          onClick={() => handleSend(message.retryMessage)}
                          className="mt-3 text-xs font-semibold text-[#047857] underline underline-offset-2 hover:text-[#065F46]"
                        >
                          Try again
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl border border-border bg-[#F8FAFC] px-4 py-3 text-sm text-[#64748B]">TaxWise is thinking…</div>
                  </div>
                )}
              </div>

              <div className="border-t border-border p-4">
                <div className="flex gap-3">
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSend();
                      }
                    }}
                    placeholder="Ask a tax question…"
                    className="flex-1 rounded-xl border border-border bg-white px-4 py-3 text-sm text-[#0F172A] placeholder:text-[#64748B]"
                  />
                  <button onClick={() => handleSend()} disabled={loading} className="rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white hover:bg-[#065F46] disabled:opacity-60">Send</button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default TaxWisePage;
