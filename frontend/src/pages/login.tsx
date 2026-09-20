import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';

const LoginPage: React.FC = () => {
  const router = useRouter();
  const { login, isLoading, error } = useAuthStore();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [localError, setLocalError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError('');

    try {
      await login(formData.email, formData.password);
      router.push('/onboarding');
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || 'Login failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-12">
      <div className="mx-auto max-w-5xl overflow-hidden rounded-[28px] border border-border bg-white shadow-soft">
        <div className="grid min-h-[720px] lg:grid-cols-[1.2fr_0.8fr]">
          <div className="bg-[#064E3B] p-10 text-white">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-lg font-semibold">T</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100">TaxWise</p>
                <p className="text-sm text-emerald-100">Personal Tax Intelligence</p>
              </div>
            </div>

            <div className="mt-16 max-w-md">
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-100">Built for Indian taxpayers</p>
              <h1 className="mt-4 text-4xl font-bold leading-tight">Understand your tax picture with clarity.</h1>
              <p className="mt-6 text-base text-emerald-50/90">
                Discover deductions, compare tax regimes, review documents, and model what-if scenarios using your actual tax profile.
              </p>
            </div>

            <div className="mt-12 space-y-4">
              {['Tax profile intelligence', 'Regime comparison', 'Document reconciliation', 'What-if scenarios'].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-emerald-50/90">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#10B981] text-xs font-bold text-[#064E3B]">✓</span>
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-center p-8 sm:p-12">
            <div className="w-full max-w-md">
              <div className="mb-8 text-center">
                <h2 className="text-3xl font-bold text-[#0F172A]">Welcome back</h2>
                <p className="mt-2 text-sm text-[#64748B]">Sign in to continue your tax workflow.</p>
              </div>

              <form className="space-y-5" onSubmit={handleSubmit}>
                {(localError || error) && (
                  <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
                    {localError || error}
                  </div>
                )}

                <div className="space-y-4">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-text">Email address</span>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                      placeholder="you@example.com"
                      value={formData.email}
                      onChange={handleChange}
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-text">Password</span>
                    <input
                      id="password"
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={handleChange}
                    />
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#065F46] disabled:opacity-60"
                >
                  {isLoading ? 'Signing in...' : 'Sign in'}
                </button>

                <div className="text-center text-sm text-[#64748B]">
                  Don’t have an account?{' '}
                  <Link href="/signup" className="font-semibold text-[#047857] hover:text-[#064E3B]">
                    Create one
                  </Link>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
