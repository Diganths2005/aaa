import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import { chatAPI, taxAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { TaxProfile } from '@/types';

type RegimeResult = {
  taxable_income: number;
  total_deductions: number;
  total_tax_liability: number;
  rebate: number;
  cess: number;
};

type ComparisonResult = {
  recommended_regime: 'old' | 'new' | 'equal';
  estimated_saving: number;
  old_regime: RegimeResult;
  new_regime: RegimeResult;
};

type ScenarioKey = 'nps' | 'investment' | 'health' | 'home-loan' | 'income' | 'regime';

const formatMoney = (value: number) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const deepCloneProfile = (profile: TaxProfile) => JSON.parse(JSON.stringify(profile)) as TaxProfile;

const computeComparison = async (profile: TaxProfile): Promise<ComparisonResult> => {
  const response = await taxAPI.compareRegimes(profile);
  const data = response.data;

  return {
    recommended_regime: data.recommended_regime,
    estimated_saving: Number(data.estimated_saving || 0),
    old_regime: {
      taxable_income: Number(data.old_regime.taxable_income || 0),
      total_deductions: Number(data.old_regime.total_deductions || 0),
      total_tax_liability: Number(data.old_regime.total_tax_liability || 0),
      rebate: Number(data.old_regime.rebate || 0),
      cess: Number(data.old_regime.cess || 0),
    },
    new_regime: {
      taxable_income: Number(data.new_regime.taxable_income || 0),
      total_deductions: Number(data.new_regime.total_deductions || 0),
      total_tax_liability: Number(data.new_regime.total_tax_liability || 0),
      rebate: Number(data.new_regime.rebate || 0),
      cess: Number(data.new_regime.cess || 0),
    },
  };
};

const getScenarioSummary = (comparison: ComparisonResult) => {
  const bestRegime = comparison.recommended_regime === 'equal' ? 'No clear winner' : comparison.recommended_regime;
  const bestTax = comparison.recommended_regime === 'old' ? comparison.old_regime.total_tax_liability : comparison.new_regime.total_tax_liability;
  return {
    bestRegime,
    bestTax,
  };
};

const WhatIfPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [currentProfile, setCurrentProfile] = useState<TaxProfile | null>(null);
  const [currentComparison, setCurrentComparison] = useState<ComparisonResult | null>(null);
  const [scenarioProfile, setScenarioProfile] = useState<TaxProfile | null>(null);
  const [scenarioComparison, setScenarioComparison] = useState<ComparisonResult | null>(null);
  const [activeScenario, setActiveScenario] = useState<ScenarioKey>('nps');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [aiAnswer, setAiAnswer] = useState('');
  const [aiSources, setAiSources] = useState<string[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
      return;
    }

    const load = async () => {
      try {
        setLoading(true);
        const response = await taxProfileAPI.getCurrentUser();
        const profile = response.data as TaxProfile;
        const comparison = await computeComparison(profile);
        setCurrentProfile(profile);
        setCurrentComparison(comparison);
        setScenarioProfile(deepCloneProfile(profile));
        setScenarioComparison(comparison);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Could not load your Tax Profile for the simulation.');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!currentComparison || !scenarioComparison) return;

    const getReason = async () => {
      try {
        const message = [
          'Explain the tax recommendation using only these actual Tax Engine results. Do not calculate anything yourself.',
          `Current situation: old regime tax ${formatMoney(currentComparison.old_regime.total_tax_liability)}, new regime tax ${formatMoney(currentComparison.new_regime.total_tax_liability)}, recommended ${currentComparison.recommended_regime}. Difference: ${formatMoney(currentComparison.estimated_saving)}.`,
          `What-if scenario: old regime tax ${formatMoney(scenarioComparison.old_regime.total_tax_liability)}, new regime tax ${formatMoney(scenarioComparison.new_regime.total_tax_liability)}, recommended ${scenarioComparison.recommended_regime}. Difference: ${formatMoney(scenarioComparison.estimated_saving)}.`,
          'Explain why the recommendation changed or stayed the same, which deductions influenced the result, and what user action would change the recommendation.',
        ].join(' ');

        const response = await chatAPI.send(message);
        setAiAnswer(response.data.answer || 'TaxWise could not explain this result right now.');
        setAiSources(response.data.sources && response.data.sources.length ? response.data.sources : ['Deterministic Tax Engine', 'Tax Profile']);
      } catch {
        setAiAnswer('TaxWise could not generate an explanation right now, but the numbers below reflect the deterministic engine output from your actual tax profile.');
        setAiSources(['Deterministic Tax Engine', 'Tax Profile']);
      }
    };

    getReason();
  }, [currentComparison, scenarioComparison]);

  const applyScenario = async (preset: ScenarioKey) => {
    if (!currentProfile) return;
    const nextProfile = deepCloneProfile(currentProfile);

    switch (preset) {
      case 'nps': {
        nextProfile.deductions = [
          ...(nextProfile.deductions || []),
          { section: '80CCD(1B)', amount: 50000, employer_contribution: 0 },
        ];
        break;
      }
      case 'investment': {
        nextProfile.investments = [
          ...(nextProfile.investments || []),
          { investment_type: 'Eligible investment', amount: 100000 },
        ];
        break;
      }
      case 'health': {
        nextProfile.deductions = [
          ...(nextProfile.deductions || []),
          { section: '80D', amount: 25000, self_health_insurance: 25000 },
        ];
        break;
      }
      case 'home-loan': {
        nextProfile.deductions = [
          ...(nextProfile.deductions || []),
          { section: '80EEA', amount: 150000, loan_amount: 150000 },
        ];
        break;
      }
      case 'income': {
        const salary = nextProfile.salary_income?.[0] || { employer_name: nextProfile.employer_name || 'Employer', gross_salary: 0, standard_deduction: 0, professional_tax: 0, tds: 0 };
        salary.gross_salary = Number(salary.gross_salary || 0) + 150000;
        nextProfile.salary_income = [salary, ...(nextProfile.salary_income || []).slice(1)];
        break;
      }
      case 'regime':
      default:
        break;
    }

    try {
      setActiveScenario(preset);
      const comparison = await computeComparison(nextProfile);
      setScenarioProfile(nextProfile);
      setScenarioComparison(comparison);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'This scenario could not be evaluated by the tax engine.');
    }
  };

  const applyProfile = async () => {
    if (!scenarioProfile || !currentProfile?.id) return;
    if (!window.confirm('Apply this temporary scenario to your real Tax Profile?')) return;

    try {
      setSaving(true);
      await taxProfileAPI.update(currentProfile.id, scenarioProfile);
      setCurrentProfile(deepCloneProfile(scenarioProfile));
      setCurrentComparison(scenarioComparison || currentComparison);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'This profile change could not be saved.');
    } finally {
      setSaving(false);
    }
  };

  const impact = useMemo(() => {
    if (!currentComparison || !scenarioComparison) return null;
    const currentBest = currentComparison.recommended_regime === 'old' ? currentComparison.old_regime.total_tax_liability : currentComparison.new_regime.total_tax_liability;
    const scenarioBest = scenarioComparison.recommended_regime === 'old' ? scenarioComparison.old_regime.total_tax_liability : scenarioComparison.new_regime.total_tax_liability;
    const delta = scenarioBest - currentBest;
    return {
      currentBest,
      scenarioBest,
      delta,
      label: delta === 0 ? 'No change' : delta > 0 ? 'Higher tax' : 'Lower tax',
    };
  }, [currentComparison, scenarioComparison]);

  const sourceBadges = [
    { icon: '🧮', label: 'Calculated by TaxWise Engine' },
    { icon: '🤖', label: 'Explained by TaxWise AI' },
    ...(aiSources.some((source) => /rag|knowledge/i.test(source)) ? [{ icon: '📚', label: 'Tax knowledge from TaxWise RAG' }] : []),
  ];

  if (!isAuthenticated || loading) {
    return <div className="min-h-screen bg-[#F8FAFC] px-4 py-10 text-[#0F172A]">{loading ? 'Loading your tax simulation…' : null}</div>;
  }

  if (!currentProfile || !currentComparison || !scenarioComparison) {
    return <div className="min-h-screen bg-[#F8FAFC] px-4 py-10 text-[#0F172A]">Simulation unavailable.</div>;
  }

  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-8 text-[#0F172A] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">What-if Simulation</p>
            <h1 className="mt-2 text-3xl font-bold text-[#0F172A]">Model a temporary tax change</h1>
          </div>
          <button onClick={applyProfile} disabled={saving} className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46] disabled:opacity-60">
            {saving ? 'Saving…' : 'Apply to profile'}
          </button>
        </header>

        {error && <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="card p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">CURRENT SITUATION</p>
            <h2 className="mt-3 text-2xl font-bold text-[#0F172A]">{formatMoney(currentComparison.recommended_regime === 'old' ? currentComparison.old_regime.total_tax_liability : currentComparison.new_regime.total_tax_liability)}</h2>
            <div className="mt-5 space-y-3 text-sm">
              <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] px-3 py-2">
                <span className="text-[#64748B]">Old Regime</span>
                <span className="font-semibold">{formatMoney(currentComparison.old_regime.total_tax_liability)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] px-3 py-2">
                <span className="text-[#64748B]">New Regime</span>
                <span className="font-semibold">{formatMoney(currentComparison.new_regime.total_tax_liability)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] px-3 py-2">
                <span className="text-[#047857]">Current Recommendation</span>
                <span className="font-semibold">
                  {currentComparison.recommended_regime === 'equal' ? 'Equal' : currentComparison.recommended_regime.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">WHAT-IF SCENARIO</p>
            <h2 className="mt-3 text-2xl font-bold text-[#0F172A]">{formatMoney(scenarioComparison.recommended_regime === 'old' ? scenarioComparison.old_regime.total_tax_liability : scenarioComparison.new_regime.total_tax_liability)}</h2>
            <div className="mt-5 space-y-3 text-sm">
              <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] px-3 py-2">
                <span className="text-[#64748B]">Old Regime</span>
                <span className="font-semibold">{formatMoney(scenarioComparison.old_regime.total_tax_liability)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] px-3 py-2">
                <span className="text-[#64748B]">New Regime</span>
                <span className="font-semibold">{formatMoney(scenarioComparison.new_regime.total_tax_liability)}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] px-3 py-2">
                <span className="text-[#047857]">Scenario Recommendation</span>
                <span className="font-semibold">
                  {scenarioComparison.recommended_regime === 'equal' ? 'Equal' : scenarioComparison.recommended_regime.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          <div className="card p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">TAX IMPACT</p>
            {impact && (
              <>
                <h2 className="mt-3 text-2xl font-bold text-[#0F172A]">{impact.delta === 0 ? '₹0' : formatMoney(Math.abs(impact.delta))}</h2>
                <div className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] px-3 py-2">
                    <span className="text-[#64748B]">Current best</span>
                    <span className="font-semibold">{formatMoney(impact.currentBest)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-[#F8FAFC] px-3 py-2">
                    <span className="text-[#64748B]">Scenario best</span>
                    <span className="font-semibold">{formatMoney(impact.scenarioBest)}</span>
                  </div>
                  <div className={`flex items-center justify-between rounded-2xl px-3 py-2 ${impact.delta <= 0 ? 'bg-[#ECFDF5] text-[#047857]' : 'bg-[#FEF2F2] text-[#DC2626]'}`}>
                    <span>{impact.label}</span>
                    <span className="font-semibold">{impact.delta === 0 ? 'No change' : `${impact.delta > 0 ? '+' : '-'}${formatMoney(Math.abs(impact.delta))}`}</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        <div className="mt-8 card p-6">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Suggested scenarios</p>
              <h2 className="mt-2 text-xl font-bold text-[#0F172A]">Explore a temporary change</h2>
            </div>
            <span className="chip">Temporary only · no automatic update</span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {[
              { key: 'nps', label: 'Invest more in NPS', summary: '+₹50,000 deduction' },
              { key: 'investment', label: 'Add eligible investment', summary: '+₹1,00,000 investment' },
              { key: 'health', label: 'Add health insurance', summary: '+₹25,000 deduction' },
              { key: 'home-loan', label: 'Add home-loan interest', summary: '+₹1,50,000 deduction' },
              { key: 'income', label: 'Change income', summary: '+₹1,50,000 salary' },
              { key: 'regime', label: 'Change regime', summary: 'Compare old vs new again' },
            ].map((scenario) => (
              <button
                key={scenario.key}
                onClick={() => applyScenario(scenario.key as ScenarioKey)}
                className={`rounded-2xl border p-4 text-left transition ${activeScenario === scenario.key ? 'border-[#10B981] bg-[#ECFDF5]' : 'border-[#E2E8F0] bg-white hover:border-[#10B981]/60'}`}
              >
                <p className="text-base font-semibold text-[#0F172A]">{scenario.label}</p>
                <p className="mt-2 text-sm text-[#64748B]">{scenario.summary}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="mt-8 card p-6">
          <div className="mb-4 flex flex-wrap gap-2">
            {sourceBadges.map((badge) => (
              <span key={badge.label} className="chip text-[11px] font-semibold tracking-wide">
                <span className="mr-1">{badge.icon}</span>
                {badge.label}
              </span>
            ))}
          </div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Why?</p>
          <h3 className="mt-3 text-2xl font-bold text-[#0F172A]">TaxWise Recommendation</h3>
          <div className="mt-5 rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] p-5">
            <p className="text-slate-700">{aiAnswer || 'TaxWise is preparing an explanation based on the actual engine result…'}</p>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#047857]">Income considered</p>
              <p className="mt-3 text-xl font-bold text-[#0F172A]">{formatMoney(scenarioComparison.new_regime.taxable_income || scenarioComparison.old_regime.taxable_income)}</p>
            </div>
            <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#047857]">Deductions considered</p>
              <p className="mt-3 text-xl font-bold text-[#0F172A]">{formatMoney(scenarioComparison.new_regime.total_deductions || scenarioComparison.old_regime.total_deductions)}</p>
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-[#E2E8F0] bg-[#ECFDF5] p-5">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Tax Rule / Source</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {aiSources.map((source) => (
                <span key={source} className="chip">{source}</span>
              ))}
            </div>
            <button className="mt-4 rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm font-semibold text-[#0F172A]">View source</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WhatIfPage;
