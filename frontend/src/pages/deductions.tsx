import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

type DeductionOpportunity = {
  title: string;
  status: 'Eligible' | 'Potentially eligible' | 'Needs confirmation' | 'Already claimed';
  reason: string;
  amount?: string;
};

const DeductionsPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [opportunities, setOpportunities] = useState<DeductionOpportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const load = async () => {
      try {
        const profileResponse = await taxProfileAPI.getCurrentUser();
        const profile = profileResponse.data;
        const list: DeductionOpportunity[] = [];

        if (profile.salary_income?.length) {
          list.push({
            title: 'Standard deduction / salary-related deductions',
            status: 'Eligible',
            reason: 'Your salary profile includes supported deduction components that are already part of the tax engine.',
            amount: 'Based on confirmed profile',
          });
        }

        if (profile.deductions?.length) {
          list.push({
            title: 'Confirmed deductions',
            status: 'Already claimed',
            reason: 'The following deductions are already captured in your current Tax Profile.',
            amount: `${profile.deductions.length} entries`,
          });
        }

        list.push(
          {
            title: 'Health insurance',
            status: 'Needs confirmation',
            reason: 'Your health insurance information may make you eligible for an additional deduction, subject to confirmation.',
            amount: 'Potential saving available',
          },
          {
            title: 'NPS-related deduction review',
            status: 'Potentially eligible',
            reason: 'Based on your confirmed profile, you may want to review NPS-related deductions.',
            amount: 'Review contribution data',
          },
          {
            title: 'Home loan interest',
            status: 'Needs confirmation',
            reason: 'If home-loan interest details are available, TaxWise can validate the claim.',
            amount: 'Requires supporting details',
          }
        );

        setOpportunities(list);
      } catch {
        setOpportunities([
          {
            title: 'Missing Tax Profile',
            status: 'Needs confirmation',
            reason: 'Complete your profile to review deduction opportunities with the deterministic engine.',
          },
        ]);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Deductions</p>
          <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Tax opportunity discovery</h1>
        </header>

        {loading ? (
          <div className="card p-8 text-sm text-[#64748B]">Reviewing deduction opportunities…</div>
        ) : (
          <div className="space-y-5">
            {opportunities.map((item) => (
              <div key={item.title} className="card p-6">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-xl font-bold text-[#0F172A]">{item.title}</p>
                    <p className="mt-1 text-sm text-[#64748B]">{item.reason}</p>
                  </div>
                  <span className="chip">{item.status}</span>
                </div>
                {item.amount && <p className="mt-4 text-sm font-semibold text-[#047857]">{item.amount}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DeductionsPage;
