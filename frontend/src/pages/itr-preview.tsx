import React, { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { itrAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import ReturnToDashboard from '@/components/ReturnToDashboard';

type Preparation = any;
const money = (value: any) => `₹${Number(value || 0).toLocaleString('en-IN')}`;

const ITRPreviewPage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [preparation, setPreparation] = useState<Preparation | null>(null);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<string[]>(['Ask me why any amount appears in this preparation.']);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!isAuthenticated) router.push('/login');
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    itrAPI.current().then((response) => setPreparation(response.data)).catch((error) => setMessage(error.response?.data?.detail || 'Could not load preparation.')).finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated || loading) return <div className="min-h-screen bg-gray-100 p-8 text-gray-700">Loading return preparation...</div>;
  if (!preparation) return <div className="min-h-screen bg-gray-100 p-8 text-red-700">{message}</div>;

  const recalculate = async () => {
    const response = await itrAPI.recalculate();
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
    const response = await itrAPI.pdf();
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
            <section><h2 className="border-b pb-2 text-lg font-semibold">Personal Information</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-gray-500">Name</dt><dd>{preparation.taxpayer.name}</dd></div><div><dt className="text-xs text-gray-500">PAN</dt><dd>{preparation.taxpayer.pan || 'Not provided'}</dd></div><div><dt className="text-xs text-gray-500">Date of birth</dt><dd>{preparation.taxpayer.date_of_birth || 'Not provided'}</dd></div><div><dt className="text-xs text-gray-500">Residential status</dt><dd>{preparation.taxpayer.residential_status}</dd></div></dl></section>
            <section><h2 className="border-b pb-2 text-lg font-semibold">Income</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['Salary/Pension', Number(income.salary) + Number(income.pension)], ['Business income', income.business_income], ['House Property', income.house_property], ['Other Sources', income.other_sources], ['Gross Total Income', income.gross_total_income]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section>
            <section><h2 className="border-b pb-2 text-lg font-semibold">Deductions and Tax Computation</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['Deductions', preparation.deductions.total], ['Taxable Income', calculation.taxable_income], ['Tax', calculation.tax], ['Rebate', calculation.rebate], ['Cess', calculation.cess], ['Total Tax', calculation.total_tax]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section>
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