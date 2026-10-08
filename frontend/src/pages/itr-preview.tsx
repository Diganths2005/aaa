import React, { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { itrAPI, taxProfileAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';
import { getProfileCompletion } from '@/lib/profile-completion';

type Preparation = any;
const money = (value: any) => `₹${Number(value || 0).toLocaleString('en-IN')}`;

const ITRPreviewPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [preparation, setPreparation] = useState<Preparation | null>(null);
  const [regime, setRegime] = useState<'old' | 'new'>('new');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<string[]>(['Ask me why any amount appears in this preparation.']);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [needsProfile, setNeedsProfile] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) router.push('/login');
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let active = true;
    const load = async () => {
      try {
        const profileResponse = await taxProfileAPI.getCurrentUser();
        if (!active) return;
        if (!getProfileCompletion(profileResponse.data).minimumReady) {
          setNeedsProfile(true);
          return;
        }
        const response = await itrAPI.current();
        if (!active) return;
        setPreparation(response.data);
        setRegime(response.data.calculation.regime);
      } catch (error: any) {
        if (active) setMessage(error.response?.data?.detail || 'Could not load preparation.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [isAuthenticated]);

  if (!isAuthenticated || loading) return <div className="min-h-screen bg-gray-100 p-8 text-gray-700">Loading return preparation...</div>;
  if (needsProfile) return <div className="min-h-screen bg-gray-100 p-8 text-gray-900"><div className="mx-auto max-w-2xl rounded-lg bg-white p-8 shadow"><h1 className="text-2xl font-bold">Complete your Tax Profile</h1><p className="mt-3 text-sm text-gray-600">Add the minimum required information before viewing personalized ITR preparation.</p><div className="mt-5 flex gap-3"><Link href="/tax-profile" className="rounded-md bg-primary px-4 py-2 text-sm text-white">Complete Profile</Link><ReturnToDashboard /></div></div></div>;
  if (!preparation) return <div className="min-h-screen bg-gray-100 p-8 text-red-700">{message}</div>;

  const recalculate = async () => {
    const response = await itrAPI.recalculate(regime, preparation.itr_form);
    setPreparation(response.data);
    setMessage('Tax recalculated from the current Tax Profile.');
  };

  const ask = async (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setMessages((current) => [...current, `You: ${question}`]);
    const response = await itrAPI.ask(question);
    setMessages((current) => [...current, response.data.assistant_message]);
    setQuestion('');
  };

  const downloadPdf = async () => {
    const response = await itrAPI.pdf(regime, preparation.itr_form);
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = `taxwise-${String(preparation.itr_form || 'itr-1').toLowerCase()}-preparation-ay-2026-27.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const income = preparation.income;
  const calculation = preparation.calculation;
  const paid = preparation.taxes_paid;

  return (
    <div className="min-h-screen bg-gray-100 px-4 py-6 lg:px-6">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-primary">TaxWise</p>
            <h1 className="mt-2 text-3xl font-bold text-gray-900">{preparation.itr_form || 'ITR'} Preparation</h1>
            <p className="mt-1 text-gray-600">Assessment Year {preparation.assessment_year}</p>
          </div>
          <ReturnToDashboard />
          {preparation.selection && <div className="mt-4 rounded-md bg-emerald-50 p-4 text-sm text-emerald-900"><p className="font-semibold">Why TaxWise selected this ITR</p><p className="mt-1">{preparation.selection.reasons?.join(' ')}</p>{preparation.selection.unsupported_conditions?.length > 0 && <p className="mt-1">Limitations: {preparation.selection.unsupported_conditions.join(' ')}</p>}</div>}
        </header>

        <div className="grid items-start gap-6 lg:grid-cols-[1.5fr_1fr]">
          <main className="space-y-6 rounded-lg bg-white p-6 shadow">
            <section className="flex flex-wrap items-end justify-between gap-3 border-b pb-4"><div><label htmlFor="tax-regime" className="block text-sm font-medium text-gray-700">Tax regime</label><select id="tax-regime" value={regime} onChange={(event) => setRegime(event.target.value as 'old' | 'new')} className="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm"><option value="new">New regime</option><option value="old">Old regime</option></select></div><p className="max-w-2xl text-xs text-amber-700">Preparation summary only. Verify all schedules with a qualified tax professional; this does not file a return.</p></section>
            <section><h2 className="border-b pb-2 text-lg font-semibold">Personal Information</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-gray-500">Name</dt><dd>{preparation.taxpayer.name}</dd></div><div><dt className="text-xs text-gray-500">PAN</dt><dd>{preparation.taxpayer.pan || 'Not provided'}</dd></div><div><dt className="text-xs text-gray-500">Date of birth</dt><dd>{preparation.taxpayer.date_of_birth || 'Not provided'}</dd></div><div><dt className="text-xs text-gray-500">Residential status</dt><dd>{preparation.taxpayer.residential_status}</dd></div></dl></section>
            <section><h2 className="border-b pb-2 text-lg font-semibold">Income</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['Salary/Pension', Number(income.salary) + Number(income.pension)], ['Business income', income.business], ['House Property', income.house_property], ['Other Sources', income.other_sources], ['Short-term capital gains', income.capital_gains?.short_term_capital_gain], ['Long-term capital gains', income.capital_gains?.long_term_capital_gain], ['Gross Total Income', income.gross_total_income]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section>
            {preparation.schedules?.capital_gains?.length > 0 && <section><h2 className="border-b pb-2 text-lg font-semibold">Capital Gains Schedule</h2><div className="mt-3 overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead><tr className="border-b text-xs text-gray-500"><th className="py-2">Asset</th><th>Holding</th><th>Section</th><th>Computed gain</th><th>Taxable gain</th><th>Tax</th></tr></thead><tbody>{preparation.schedules.capital_gains.map((item: any, index: number) => <tr key={`${item.asset_type}-${index}`} className="border-b"><td className="py-2">{item.asset_type.replace(/_/g, ' ')}</td><td>{item.holding_period.replace(/_/g, ' ')}</td><td>{item.applicable_section}</td><td>{money(item.computed_gain)}</td><td>{money(item.taxable_gain)}</td><td>{money(item.tax)}</td></tr>)}</tbody></table></div></section>}
            {preparation.schedules?.business_income?.length > 0 && <section><h2 className="border-b pb-2 text-lg font-semibold">Business Income Schedule</h2><div className="mt-3 overflow-x-auto"><table className="w-full min-w-[560px] text-left text-sm"><thead><tr className="border-b text-xs text-gray-500"><th className="py-2">Business</th><th>Nature</th><th>Gross receipts</th><th>Net profit / loss</th><th>Presumptive section</th></tr></thead><tbody>{preparation.schedules.business_income.map((item: any, index: number) => <tr key={`${item.business_name}-${index}`} className="border-b"><td className="py-2">{item.business_name}</td><td>{item.nature_of_business}</td><td>{money(item.gross_receipts)}</td><td>{money(item.net_profit_or_loss)}</td><td>{item.presumptive_section || 'Not specified'}</td></tr>)}</tbody></table><p className="mt-2 text-xs text-amber-700">Business profit is user-entered. TaxWise does not prepare full books, depreciation, or statutory business schedules.</p></div></section>}
            <section><h2 className="border-b pb-2 text-lg font-semibold">Deductions and Tax Computation</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['Deductions', preparation.deductions.total], ['Taxable Income', calculation.taxable_income], ['Tax', calculation.tax], ['Rebate', calculation.rebate], ['Cess', calculation.cess], ['Total Tax', calculation.total_tax]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl><details className="mt-4 border-t pt-4"><summary className="cursor-pointer text-sm font-semibold text-primary">Why this result?</summary><div className="mt-3 space-y-2 text-sm"><p>Ordinary taxable income through slabs: {money(calculation.ordinary_taxable_income)}</p>{calculation.slab_calculation?.map((step: any, index: number) => <p key={`${step.lower_bound}-${index}`} className="text-gray-600">{step.upper_bound === null ? `Above ${money(step.lower_bound)}` : `${money(step.lower_bound)} to ${money(step.upper_bound)}`}: {money(step.taxable_amount)} at {Number(step.rate) * 100}% = {money(step.tax)}</p>)}<p>Tax before rebate: {money(calculation.tax_before_rebate)}</p><p>Rebate: {money(calculation.rebate)}</p><p>Tax after rebate: {money(calculation.tax_after_rebate)}</p><p>Surcharge: {money(calculation.surcharge)}</p><p>Cess: {money(calculation.cess)}</p><p>Final tax liability: {money(calculation.total_tax)}</p></div></details></section>
            <section><h2 className="border-b pb-2 text-lg font-semibold">Taxes Paid</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['TDS', paid.tds], ['Total Paid', paid.total], ['Refund', calculation.refund], ['Payable', calculation.payable]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section>
            {preparation.support_status && <section><h2 className="border-b pb-2 text-lg font-semibold">Support status</h2><div className="mt-3 space-y-2 text-sm">{Object.entries(preparation.support_status).map(([label, value]) => <p key={label} className="flex justify-between gap-4"><span>{label.replace(/_/g, ' ')}</span><span className="font-semibold">{String(value)}</span></p>)}</div></section>}
            {message && <p className="rounded bg-emerald-50 p-3 text-sm text-emerald-800">{message}</p>}
            <div className="flex flex-wrap gap-3"><button type="button" onClick={recalculate} className="rounded-md bg-primary px-4 py-2 text-sm text-white">Recalculate</button><button type="button" onClick={downloadPdf} className="rounded-md border px-4 py-2 text-sm">Download preparation PDF</button><Link href="/dashboard" className="rounded-md border px-4 py-2 text-sm">Dashboard</Link></div>
          </main>

          <aside className="rounded-lg bg-slate-900 p-5 text-slate-100 shadow"><h2 className="text-xl font-semibold text-white">Ask about this result</h2><div className="mt-4 min-h-[280px] space-y-3 text-sm">{messages.map((item, index) => <p key={`${item}-${index}`} className="rounded bg-slate-800 p-3 text-slate-100">{item}</p>)}</div><form onSubmit={ask} className="mt-4 flex gap-2"><input value={question} onChange={(event) => setQuestion(event.target.value)} className="min-w-0 flex-1 rounded px-3 py-2 text-slate-900" placeholder="Why is this amount shown?" /><button type="submit" className="rounded bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-900">Ask</button></form></aside>
        </div>
      </div>
    </div>
  );
};

export default ITRPreviewPage;