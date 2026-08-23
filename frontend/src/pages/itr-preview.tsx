import React, { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { itrAPI } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

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

  useEffect(() => { if (!isAuthenticated) router.push('/login'); }, [isAuthenticated, router]);
  useEffect(() => {
    if (!isAuthenticated) return;
    itrAPI.current().then((response) => setPreparation(response.data)).catch((error) => setMessage(error.response?.data?.detail || 'Could not load ITR-1 preparation.')).finally(() => setLoading(false));
  }, [isAuthenticated]);

  if (!isAuthenticated || loading) return <div className="min-h-screen bg-gray-100 p-8 text-gray-700">Loading ITR-1 preparation...</div>;
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
    link.download = 'taxwise-itr1-preparation-ay-2026-27.pdf';
    link.click();
    URL.revokeObjectURL(url);
  };
  const income = preparation.income;
  const calculation = preparation.calculation;
  const paid = preparation.taxes_paid;

  return <div className="min-h-screen bg-gray-100 px-4 py-6 lg:px-6"><div className="mx-auto max-w-7xl"><header className="mb-6"><p className="text-sm font-semibold uppercase tracking-wide text-primary">TaxWise</p><h1 className="mt-2 text-3xl font-bold text-gray-900">ITR-1 Preparation</h1><p className="mt-1 text-gray-600">Assessment Year {preparation.assessment_year}</p></header><div className="grid items-start gap-6 lg:grid-cols-[1.5fr_1fr]"><main className="space-y-6 rounded-lg bg-white p-6 shadow"><section><h2 className="border-b pb-2 text-lg font-semibold">Personal Information</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2"><div><dt className="text-xs text-gray-500">Name</dt><dd>{preparation.taxpayer.name}</dd></div><div><dt className="text-xs text-gray-500">PAN</dt><dd>{preparation.taxpayer.pan || 'Not provided'}</dd></div><div><dt className="text-xs text-gray-500">Date of birth</dt><dd>{preparation.taxpayer.date_of_birth || 'Not provided'}</dd></div><div><dt className="text-xs text-gray-500">Residential status</dt><dd>{preparation.taxpayer.residential_status}</dd></div></dl></section><section><h2 className="border-b pb-2 text-lg font-semibold">Income</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['Salary/Pension', Number(income.salary) + Number(income.pension)], ['House Property', income.house_property], ['Other Sources', income.other_sources], ['Gross Total Income', income.gross_total_income]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section><section><h2 className="border-b pb-2 text-lg font-semibold">Deductions and Tax Computation</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['Deductions', preparation.deductions.total], ['Taxable Income', calculation.taxable_income], ['Tax', calculation.tax], ['Rebate', calculation.rebate], ['Cess', calculation.cess], ['Total Tax', calculation.total_tax]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section><section><h2 className="border-b pb-2 text-lg font-semibold">Taxes Paid and Final Result</h2><dl className="mt-3 grid gap-3 sm:grid-cols-2">{[['TDS', paid.tds], ['Advance Tax', paid.advance_tax], ['Total Tax Paid', paid.total], ['Refund', calculation.refund], ['Tax Payable', calculation.payable]].map(([label, value]) => <div key={label as string}><dt className="text-xs text-gray-500">{label}</dt><dd>{money(value)}</dd></div>)}</dl></section><div className="flex flex-wrap gap-3 border-t pt-5"><Link href="/tax-profile"><button className="rounded-md border px-4 py-2 text-sm">Edit Profile</button></Link><button onClick={recalculate} className="rounded-md bg-primary px-4 py-2 text-sm text-white">Recalculate</button><button onClick={downloadPdf} className="rounded-md bg-green-600 px-4 py-2 text-sm text-white">Generate PDF</button></div>{message && <p className="text-sm text-gray-600" role="status">{message}</p>}</main><aside className="flex min-h-[520px] flex-col rounded-lg bg-slate-900 p-5 text-white shadow lg:sticky lg:top-6 lg:max-h-[calc(100vh-48px)]"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">TaxWise Assistant</p><h2 className="mt-2 text-2xl font-semibold">Understand your result</h2><div className="flex-1 space-y-3 overflow-y-auto py-5" aria-live="polite">{messages.map((item, index) => <p key={`${item}-${index}`} className={`rounded-lg px-3 py-2 text-sm ${item.startsWith('You:') ? 'ml-auto bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-200'}`}>{item}</p>)}</div><form onSubmit={ask} className="flex gap-2 border-t border-slate-700 pt-4"><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Why is my tax this amount?" className="min-w-0 flex-1 rounded-md border-0 px-3 py-2 text-sm text-slate-900" /><button className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-semibold text-slate-950">Ask</button></form></aside></div></div></div>;
};

export default ITRPreviewPage;