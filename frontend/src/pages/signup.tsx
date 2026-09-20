import React, { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuthStore } from '@/store/auth';

const SignupPage: React.FC = () => {
  const router = useRouter();
  const { signup, isLoading, error } = useAuthStore();
  const [formData, setFormData] = useState({
    email: '',
    firstName: '',
    lastName: '',
    password: '',
    confirmPassword: '',
  });
  const [localError, setLocalError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError('');

    if (formData.password !== formData.confirmPassword) {
      setLocalError('Passwords do not match');
      return;
    }

    try {
      await signup(formData.email, formData.firstName, formData.lastName, formData.password);
      router.push('/onboarding');
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || 'Signup failed');
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-12">
      <div className="mx-auto max-w-5xl overflow-hidden rounded-[28px] border border-border bg-white shadow-soft">
        <div className="grid min-h-[780px] lg:grid-cols-[1.1fr_0.9fr]">
          <div className="bg-[#064E3B] p-10 text-white">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-lg font-semibold">T</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100">TaxWise</p>
                <p className="text-sm text-emerald-100">Personal Tax Intelligence</p>
              </div>
            </div>

            <div className="mt-16 max-w-md">
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-100">Start your tax journey</p>
              <h1 className="mt-4 text-4xl font-bold leading-tight">Set up a tax profile that understands you.</h1>
              <p className="mt-6 text-base text-emerald-50/90">
                Build your personal tax profile, review your documents, and prepare for a more informed ITR season.
              </p>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-2">
              {['Income review', 'Deductions', 'Regime check', 'File readiness'].map((item) => (
                <div key={item} className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-emerald-50/90">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-center p-8 sm:p-12">
            <div className="w-full max-w-md">
              <div className="mb-8 text-center">
                <h2 className="text-3xl font-bold text-[#0F172A]">Create account</h2>
                <p className="mt-2 text-sm text-[#64748B]">Get your TaxWise workspace ready.</p>
              </div>

              <form className="space-y-5" onSubmit={handleSubmit}>
                {(localError || error) && (
                  <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm font-medium text-red-700">
                    {localError || error}
                  </div>
                )}

                <div className="grid gap-4 sm:grid-cols-2">
                  <input
                    name="firstName"
                    type="text"
                    required
                    className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                    placeholder="First name"
                    value={formData.firstName}
                    onChange={handleChange}
                  />
                  <input
                    name="lastName"
                    type="text"
                    required
                    className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                    placeholder="Last name"
                    value={formData.lastName}
                    onChange={handleChange}
                  />
                </div>

                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                  placeholder="Email address"
                  value={formData.email}
                  onChange={handleChange}
                />

                <input
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                  placeholder="Password"
                  value={formData.password}
                  onChange={handleChange}
                />

                <input
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  required
                  className="w-full rounded-xl border border-border bg-white px-3 py-3 text-sm text-text placeholder:text-muted"
                  placeholder="Confirm password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                />

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full rounded-xl bg-[#047857] px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#065F46] disabled:opacity-60"
                >
                  {isLoading ? 'Creating account...' : 'Create account'}
                </button>

                <div className="text-center text-sm text-[#64748B]">
                  Already have an account?{' '}
                  <Link href="/login" className="font-semibold text-[#047857] hover:text-[#064E3B]">
                    Sign in
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

export default SignupPage;
