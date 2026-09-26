import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';
import { chatAPI } from '@/lib/api';
import ReturnToDashboard from '@/components/ReturnToDashboard';

type Message = {
  role: 'user' | 'assistant';
  text: string;
  retryMessage?: string;
};

const suggestedPrompts = [
  'Why is my tax this high?',
  'Which regime is better for me?',
  'What deductions may I be eligible for?',
  'Did TaxWise find anything I missed?',
  'Am I ready to file?',
  'What if I invest ₹50,000 more in NPS?',
];

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

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

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
            <div className="mt-5 space-y-3 text-sm text-[#64748B]">
              <div className="flex items-center gap-2"><span className="text-[#047857]">✓</span> Salary confirmed from profile</div>
              <div className="flex items-center gap-2"><span className="text-[#047857]">✓</span> TDS confirmed</div>
              <div className="flex items-center gap-2"><span className="text-[#047857]">✓</span> 80C-related deductions reviewed</div>
              <div className="flex items-center gap-2"><span className="text-[#F59E0B]">⚠</span> Health insurance needs confirmation</div>
              <div className="flex items-center gap-2"><span className="text-[#64748B]">○</span> Bank interest missing</div>
            </div>

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
                      <p className="whitespace-pre-wrap text-sm leading-6">{message.text}</p>
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
