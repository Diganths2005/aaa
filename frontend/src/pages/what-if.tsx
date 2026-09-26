import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/router';
import { chatAPI, taxAPI, taxProfileAPI, whatIfAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';
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

type ScenarioKey = 'nps' | 'investment' | 'health' | 'home-loan' | 'income' | 'regime' | 'custom';

type ScenarioEntry = {
  id: number;
  label: string;
  field: string;
  operation: string;
  value: any;
  index?: number;
};

const formatMoney = (value: number) => `₹${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const deepCloneProfile = (profile: TaxProfile) => JSON.parse(JSON.stringify(profile)) as TaxProfile;

const buildCustomScenarioEntry = (draft: { type: string; section: string; amount: string; index?: number }) => {
  const amount = Number(draft.amount || 0);
  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error('Enter a valid amount greater than zero.');
  }

  if (draft.type === 'deduction') {
    return {
      id: Date.now() + Math.random(),
      label: `Add ${draft.section} deduction`,
      field: 'deductions',
      operation: 'add',
      value: { section: draft.section, amount },
    } as ScenarioEntry;
  }

  if (draft.type === 'salary') {
    return {
      id: Date.now() + Math.random(),
      label: `Increase salary by ${formatMoney(amount)}`,
      field: 'salary_income',
      operation: 'increase_by',
      value: amount,
      index: 0,
    } as ScenarioEntry;
  }

  if (draft.type === 'tds') {
    return {
      id: Date.now() + Math.random(),
      label: `Increase TDS by ${formatMoney(amount)}`,
      field: 'taxes_paid',
      operation: 'add',
      value: { tax_type: 'tds', amount },
    } as ScenarioEntry;
  }

  throw new Error('Unsupported scenario type.');
};

const computeComparison = async (profile: TaxProfile): Promise<ComparisonResult> => {
  const response = await taxAPI.compareRegimes(profile, true);
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

const comparisonFromSimulation = (data: any): ComparisonResult => {
  const regimes = data.comparison.what_if_regimes;
  const toResult = (result: any): RegimeResult => ({
    taxable_income: Number(result.taxable_income || 0),
    total_deductions: Number(result.total_deductions || 0),
    total_tax_liability: Number(result.total_tax_liability || 0),
    rebate: Number(result.rebate || 0),
    cess: Number(result.cess || 0),
  });
  return { recommended_regime: regimes.recommended, estimated_saving: 0, old_regime: toResult(regimes.old), new_regime: toResult(regimes.new) };
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
  const { isAuthenticated, hydrate } = useAuthStore();
  const [authHydrated, setAuthHydrated] = useState(false);
  const [currentProfile, setCurrentProfile] = useState<TaxProfile | null>(null);
  const [currentComparison, setCurrentComparison] = useState<ComparisonResult | null>(null);
  const [scenarioProfile, setScenarioProfile] = useState<TaxProfile | null>(null);
  const [scenarioComparison, setScenarioComparison] = useState<ComparisonResult | null>(null);
  const [activeScenario, setActiveScenario] = useState<ScenarioKey | null>(null);
  const [scenarioChanges, setScenarioChanges] = useState<Array<{ field: string; operation: string; value: unknown; index?: number }>>([]);
  const [customScenarios, setCustomScenarios] = useState<ScenarioEntry[]>([]);
  const [scenarioDraft, setScenarioDraft] = useState({ type: 'deduction', section: '80C', amount: '100000' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [aiAnswer, setAiAnswer] = useState('');
  const [aiSources, setAiSources] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    hydrate();
    setAuthHydrated(true);
  }, [hydrate]);

  useEffect(() => {
    if (!authHydrated) return;
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
  }, [authHydrated, isAuthenticated, router]);

  useEffect(() => {
    if (!currentComparison || !scenarioComparison) return;

    const getReason = async () => {
      try {
        const message = [
          'Explain the tax recommendation using only these calculated results. Do not calculate anything yourself.',
          `Current situation: old regime tax ${formatMoney(currentComparison.old_regime.total_tax_liability)}, new regime tax ${formatMoney(currentComparison.new_regime.total_tax_liability)}, recommended ${currentComparison.recommended_regime}. Difference: ${formatMoney(currentComparison.estimated_saving)}.`,
          `What-if scenario: old regime tax ${formatMoney(scenarioComparison.old_regime.total_tax_liability)}, new regime tax ${formatMoney(scenarioComparison.new_regime.total_tax_liability)}, recommended ${scenarioComparison.recommended_regime}. Difference: ${formatMoney(scenarioComparison.estimated_saving)}.`,
          'Explain why the recommendation changed or stayed the same, which deductions influenced the result, and what user action would change the recommendation.',
        ].join(' ');

        const response = await chatAPI.send(message);
        setAiAnswer(response.data.answer || 'TaxWise could not explain this result right now.');
        setAiSources(response.data.sources && response.data.sources.length ? response.data.sources : ['Current calculation', 'Your Tax Profile']);
      } catch {
        setAiAnswer('TaxWise could not generate an explanation right now, but the numbers below reflect the deterministic engine output from your actual tax profile.');
        setAiSources(['Current calculation', 'Your Tax Profile']);
      }
    };

    getReason();
  }, [currentComparison, scenarioComparison]);

  const runScenarioChanges = async (changes: Array<{ field: string; operation: string; value: unknown; index?: number }>, scenarioKey: ScenarioKey | 'custom' = 'custom') => {
    if (!currentProfile || !changes.length) return;

    try {
      setActiveScenario(scenarioKey);
      setScenarioChanges(changes);
      const response = await whatIfAPI.simulate(changes, currentProfile.id);
      setScenarioProfile(response.data.what_if.profile);
      setScenarioComparison(comparisonFromSimulation(response.data));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'This scenario could not be evaluated with the current profile.');
    }
  };

  const applyScenario = async (preset: ScenarioKey) => {
    if (!currentProfile) return;
    const changes = preset === 'nps'
      ? [{ field: 'deductions', operation: 'add', value: { section: '80CCD(1B)', amount: 50000, employer_contribution: 0 } }]
      : preset === 'investment'
        ? [{ field: 'deductions', operation: 'add', value: { section: '80C', amount: 100000 } }]
        : preset === 'health'
          ? [{ field: 'deductions', operation: 'add', value: { section: '80D', amount: 25000, self_health_insurance: 25000 } }]
          : preset === 'home-loan'
            ? [{ field: 'deductions', operation: 'add', value: { section: '80EEA', amount: 150000, loan_amount: 150000 } }]
            : preset === 'income'
              ? [{ field: 'salary_income', operation: 'increase_by', value: 150000, index: 0 }]
              : preset === 'regime'
                ? [{ field: 'regime', operation: 'replace', value: 'old' }]
                : [];

    await runScenarioChanges(changes, preset);
  };

  const addCustomScenario = async () => {
    try {
      const entry = buildCustomScenarioEntry(scenarioDraft);
      const next = [...customScenarios, entry];
      setCustomScenarios(next);
      const changes = next.map(({ field, operation, value, index }) => ({ field, operation, value, index }));
      await runScenarioChanges(changes, 'custom');
    } catch (err: any) {
      setError(err.message || 'Please enter a valid custom scenario amount.');
    }
  };

  const removeCustomScenario = async (id: number) => {
    const next = customScenarios.filter((item) => item.id !== id);
    setCustomScenarios(next);
    const changes = next.map(({ field, operation, value, index }) => ({ field, operation, value, index }));
    if (changes.length) {
      await runScenarioChanges(changes, 'custom');
    } else {
      setScenarioChanges([]);
      setActiveScenario(null);
      setScenarioComparison(currentComparison);
    }
  };

  const applyProfile = async () => {
    if (!scenarioProfile || !currentProfile?.id || !scenarioChanges.length) return;
    if (!window.confirm('Apply this temporary scenario to your real Tax Profile?')) return;

    try {
      setSaving(true);
      setError('');
      setSuccess('');
      await whatIfAPI.apply(scenarioChanges, currentProfile.id);
      setCurrentProfile(deepCloneProfile(scenarioProfile));
      setCurrentComparison(scenarioComparison || currentComparison);
      setSuccess('Your scenario has been applied to your Tax Profile.');
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
      oldDelta: scenarioComparison.old_regime.total_tax_liability - currentComparison.old_regime.total_tax_liability,
      newDelta: scenarioComparison.new_regime.total_tax_liability - currentComparison.new_regime.total_tax_liability,
      label: delta === 0 ? 'No change' : delta > 0 ? 'Higher tax' : 'Lower tax',
    };
  }, [currentComparison, scenarioComparison]);

  const sourceBadges = [
    { icon: '🧮', label: 'Calculated by TaxWise Engine' },
    { icon: '🤖', label: 'Explained by TaxWise AI' },
  ];

  if (!authHydrated || !isAuthenticated || loading) {
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
          <div className="flex flex-wrap gap-3">
            <ReturnToDashboard />
            <button onClick={applyProfile} disabled={saving || !activeScenario} className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46] disabled:opacity-60">
              {saving ? 'Saving…' : activeScenario ? 'Apply to profile' : 'Choose a scenario first'}
            </button>
          </div>
        </header>

        {error && <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
        {success && <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{success}</div>}

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
                  {impact.delta === 0 && (impact.oldDelta !== 0 || impact.newDelta !== 0) && (
                    <p className="rounded-2xl bg-[#FFFBEB] px-3 py-2 text-xs text-[#92400E]">
                      Old regime: {impact.oldDelta < 0 ? `${formatMoney(Math.abs(impact.oldDelta))} lower` : `${formatMoney(impact.oldDelta)} higher`}. New regime: no change.
                    </p>
                  )}
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
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#047857]">Custom scenario builder</p>
              <h2 className="mt-2 text-xl font-bold text-[#0F172A]">Add your own simulation</h2>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <select
              value={scenarioDraft.type}
              onChange={(event) => setScenarioDraft((draft) => ({ ...draft, type: event.target.value }))}
              className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm"
            >
              <option value="deduction">Deduction</option>
              <option value="salary">Salary income</option>
              <option value="tds">TDS</option>
            </select>

            {scenarioDraft.type === 'deduction' ? (
              <select
                value={scenarioDraft.section}
                onChange={(event) => setScenarioDraft((draft) => ({ ...draft, section: event.target.value }))}
                className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm"
              >
                <option value="80C">80C</option>
                <option value="80D">80D</option>
                <option value="80CCD(1B)">80CCD(1B)</option>
                <option value="80EEA">80EEA</option>
                <option value="80G">80G</option>
              </select>
            ) : (
              <div className="rounded-xl border border-dashed border-[#CBD5E1] bg-[#F8FAFC] px-3 py-2 text-sm text-[#64748B] flex items-center">
                {scenarioDraft.type === 'salary' ? 'Salary income' : 'TDS payment'}
              </div>
            )}

            <input
              type="number"
              min="1"
              value={scenarioDraft.amount}
              onChange={(event) => setScenarioDraft((draft) => ({ ...draft, amount: event.target.value }))}
              placeholder="Amount"
              className="rounded-xl border border-[#E2E8F0] bg-white px-3 py-2 text-sm"
            />

            <button
              onClick={addCustomScenario}
              className="rounded-xl bg-[#047857] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#065F46]"
            >
              Add scenario
            </button>
          </div>

          {customScenarios.length > 0 && (
            <div className="mt-5 space-y-3">
              {customScenarios.map((item) => (
                <div key={item.id} className="flex items-center justify-between rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] px-4 py-3">
                  <div>
                    <p className="font-semibold text-[#0F172A]">{item.label}</p>
                    <p className="text-xs text-[#64748B]">{item.field} · {item.operation}</p>
                  </div>
                  <button
                    onClick={() => removeCustomScenario(item.id)}
                    className="rounded-lg border border-[#E2E8F0] bg-white px-2 py-1 text-xs font-semibold text-[#0F172A]"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
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
