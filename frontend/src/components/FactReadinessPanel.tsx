import React, { useCallback, useEffect, useState } from 'react';
import { factsAPI } from '@/lib/api';

type FactEvidence = {
  id: string;
  source_type: string;
  document_name?: string | null;
  page_number?: number | null;
  section?: string | null;
  source_text?: string | null;
  confidence: string;
};

type TaxpayerFact = {
  id: string;
  fact_key: string;
  value: unknown;
  status: string;
  source_type: string;
  confidence: string;
  group_id?: string | null;
  evidence: FactEvidence[];
};

type Requirement = {
  key: string;
  label: string;
  section: string;
  status: string;
  required: boolean;
  applicable: boolean;
};

const statusClass: Record<string, string> = {
  CONFIRMED: 'bg-emerald-100 text-emerald-800',
  CONFLICT: 'bg-amber-100 text-amber-800',
  NEEDS_CONFIRMATION: 'bg-amber-100 text-amber-800',
  EXTRACTED: 'bg-sky-100 text-sky-800',
  REJECTED: 'bg-slate-100 text-slate-600',
  NOT_APPLICABLE: 'bg-slate-100 text-slate-600',
  MISSING: 'bg-rose-100 text-rose-800',
};

const displayValue = (value: unknown) => typeof value === 'string'
  ? value
  : JSON.stringify(value);

const FactReadinessPanel: React.FC = () => {
  const [facts, setFacts] = useState<TaxpayerFact[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [readiness, setReadiness] = useState(0);
  const [determination, setDetermination] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [corrections, setCorrections] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    const [factResponse, readinessResponse, determinationResponse] = await Promise.all([
      factsAPI.list(),
      factsAPI.readiness(),
      factsAPI.determination(),
    ]);
    setFacts(factResponse.data);
    setRequirements(readinessResponse.data.requirements || []);
    setReadiness(readinessResponse.data.readiness_percent || 0);
    setDetermination(determinationResponse.data.recommended_itr || 'Needs review');
  }, []);

  useEffect(() => {
    load()
      .catch(() => setError('Could not load taxpayer facts and readiness. Please try again.'))
      .finally(() => setLoading(false));
  }, [load]);

  const resolve = async (fact: TaxpayerFact, action: 'confirm' | 'reject' | 'keep' | 'accept' | 'correct') => {
    setSaving(fact.id);
    setError('');
    try {
      await factsAPI.resolve(fact.id, action, action === 'correct' ? corrections[fact.id] : undefined);
      setCorrections((current) => ({ ...current, [fact.id]: '' }));
      await load();
    } catch (resolveError: any) {
      const detail = resolveError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not resolve this fact. Please try again.');
    } finally {
      setSaving(null);
    }
  };

  if (loading) return <section className="surface-panel p-5 text-sm text-slate-500">Loading fact readiness…</section>;

  const reviewFacts = facts.filter((fact) => ['EXTRACTED', 'NEEDS_CONFIRMATION', 'CONFLICT'].includes(fact.status));
  const missing = requirements.filter((item) => item.required && item.applicable && item.status === 'MISSING');

  return (
    <section className="surface-panel space-y-5 p-5 sm:p-7" aria-labelledby="fact-readiness-heading">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-kicker">Evidence-backed profile</p>
          <h2 id="fact-readiness-heading" className="mt-1 text-xl font-semibold text-slate-950">Facts and filing readiness</h2>
          <p className="mt-1 text-sm text-slate-500">Review source evidence and resolve conflicts; only confirmed mapped facts update your return profile.</p>
        </div>
        <div className="min-w-40">
          <p className="text-sm font-semibold text-slate-700">{determination}</p>
          <p className="mt-1 text-xs text-slate-500">{readiness}% fact readiness</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${readiness}%` }} />
          </div>
        </div>
      </header>

      {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}

      {missing.length > 0 && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
          <h3 className="text-sm font-semibold text-rose-900">Missing required information</h3>
          <ul className="mt-2 list-inside list-disc text-sm text-rose-800">
            {missing.map((item) => <li key={item.key}>{item.label} · {item.section}</li>)}
          </ul>
        </div>
      )}

      {reviewFacts.length === 0 ? (
        <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-600">No extracted facts are waiting for review. Upload documents or edit the structured profile to record confirmed information.</p>
      ) : (
        <div className="space-y-3">
          {reviewFacts.map((fact) => {
            const sensitive = /pan|aadhaar|account_number/i.test(fact.fact_key);
            return (
              <article key={fact.id} className="rounded-xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-semibold text-slate-900">{fact.fact_key.replace(/[._]/g, ' ')}</h3>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass[fact.status] || statusClass.NEEDS_CONFIRMATION}`}>{fact.status.replace(/_/g, ' ')}</span>
                </div>
                <p className="mt-2 break-words text-sm text-slate-700">{displayValue(fact.value)}</p>
                <div className="mt-3 space-y-2">
                  {fact.evidence.map((evidence) => (
                    <div key={evidence.id} className="rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      <p className="font-medium">{evidence.document_name || evidence.source_type}{evidence.page_number ? ` · Page ${evidence.page_number}` : ''} · {evidence.confidence} confidence</p>
                      {evidence.section && <p>{evidence.section}</p>}
                      {evidence.source_text && <p className="mt-1">{evidence.source_text}</p>}
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {fact.status !== 'CONFLICT' && (
                    <>
                      <button type="button" onClick={() => void resolve(fact, 'confirm')} disabled={saving === fact.id} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Confirm</button>
                      <button type="button" onClick={() => void resolve(fact, 'reject')} disabled={saving === fact.id} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 disabled:opacity-50">Reject</button>
                    </>
                  )}
                  {fact.status === 'CONFLICT' && (
                    <>
                      <button type="button" onClick={() => void resolve(fact, 'keep')} disabled={saving === fact.id} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 disabled:opacity-50">Keep confirmed value</button>
                      <button type="button" onClick={() => void resolve(fact, 'accept')} disabled={saving === fact.id} className="rounded-lg bg-amber-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Accept this value</button>
                    </>
                  )}
                  {!sensitive && (
                    <div className="flex min-w-full flex-wrap gap-2 pt-1">
                      <input
                        value={corrections[fact.id] || ''}
                        onChange={(event) => setCorrections((current) => ({ ...current, [fact.id]: event.target.value }))}
                        aria-label={`Correct ${fact.fact_key}`}
                        placeholder="Enter a corrected value"
                        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      />
                      <button type="button" onClick={() => void resolve(fact, 'correct')} disabled={saving === fact.id || !corrections[fact.id]?.trim()} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 disabled:opacity-50">Save correction</button>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default FactReadinessPanel;
