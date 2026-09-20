import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/store/auth';
import { documentsAPI, onboardingAPI, taxProfileAPI } from '@/lib/api';
import { TaxProfile } from '@/types';

const inputClass = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm';
const apiErrorMessage = (error: any, fallback: string) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const location = Array.isArray(item?.loc) ? item.loc.filter(Boolean).join('.') : '';
      return location ? `${location}: ${item.msg || 'Invalid value'}` : item.msg || 'Invalid value';
    }).join(' ');
  }
  return fallback;
};
const blankProfile: TaxProfile = {
  residential_status: 'resident', employment_type: 'salaried', financial_year: '2025-26', assessment_year: '2026-27',
  is_senior_citizen: false, is_director: false, has_unlisted_equity: false, has_foreign_assets: false,
  has_foreign_income: false, has_business_income: false, has_speculative_income: false, has_carry_forward_loss: false,
  salary_income: [], pension_income: [], house_properties: [], other_income: [], capital_gains: [], business_income: [],
  foreign_income_assets: [], investments: [], deductions: [], taxes_paid: [], bank_accounts: [], documents: [],
};

const TaxProfilePage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<TaxProfile>(blankProfile);
  const [files, setFiles] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [assistantInput, setAssistantInput] = useState('');
  const [assistantMessages, setAssistantMessages] = useState<string[]>([]);
  const [proposal, setProposal] = useState<{ salary?: number; tds?: number } | null>(null);
  const [documentCandidates, setDocumentCandidates] = useState<Array<{ field: string; value: string; page: number }> | null>(null);
  const [documentProcessing, setDocumentProcessing] = useState(false);
  const [progress, setProgress] = useState({ completed: 0, total: 16, percent: 0 });
  const hydrated = useRef(false);

  useEffect(() => { if (!isAuthenticated) router.push('/login'); }, [isAuthenticated, router]);
  useEffect(() => {
    if (!isAuthenticated) return;
    onboardingAPI.getSession().then((response) => {
      setAssistantMessages([response.data.assistant_message]);
      setProgress(response.data.progress);
      if (response.data.profile) {
        setFormData({ ...blankProfile, ...response.data.profile });
        hydrated.current = true;
      }
    }).catch(() => setAssistantMessages(['Hi! I\'ll help you complete your Tax Profile.']))
      .finally(() => { hydrated.current = true; });
    taxProfileAPI.getCurrentUser().then((response) => {
      setFormData({ ...blankProfile, ...response.data });
      hydrated.current = true;
    }).catch(() => { hydrated.current = true; });
  }, [isAuthenticated]);
  if (!isAuthenticated) return null;

  const update = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = event.target;
    setFormData((current) => ({ ...current, [name]: type === 'checkbox' ? (event.target as HTMLInputElement).checked : type === 'number' ? Number(value) : value }));
  };
  const add = (key: keyof TaxProfile, value: object) => setFormData((current) => ({ ...current, [key]: [...(current[key] as object[]), value] }));
  const remove = (key: keyof TaxProfile, index: number) => setFormData((current) => ({ ...current, [key]: (current[key] as object[]).filter((_, itemIndex) => itemIndex !== index) }));
  const updateEntry = (key: keyof TaxProfile, index: number, field: string, value: string | number | boolean) => setFormData((current) => ({ ...current, [key]: (current[key] as object[]).map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item) }));

  const addSalary = () => add('salary_income', { employer_name: '', gross_salary: 0, standard_deduction: 0, professional_tax: 0, tds: 0 });
  const addProperty = () => add('house_properties', { property_type: 'self_occupied', city: '', annual_rent: 0, municipal_tax: 0, home_loan_interest: 0, ownership_share: 100, loan_purpose: 'purchase_or_construction', loan_sanction_date: '', construction_completed_within_five_years: false });
  const addOther = () => add('other_income', { income_type: 'interest', description: '', amount: 0, tds: 0 });
  const addPension = () => add('pension_income', { payer_name: '', amount: 0, tds: 0 });
  const addCapitalGain = () => add('capital_gains', { asset_type: 'equity', holding_period: 'short_term', sale_value: 0, cost_of_acquisition: 0, transfer_expenses: 0, gain_or_loss: 0 });
  const addBusiness = () => add('business_income', { business_name: '', nature_of_business: '', gross_receipts: 0, net_profit_or_loss: 0 });
  const addForeign = () => add('foreign_income_assets', { country: '', item_type: 'income', description: '', value: 0 });
  const addTax = () => add('taxes_paid', { tax_type: 'tds', amount: 0, reference: '' });
  const addInvestment = () => add('investments', { investment_type: '', amount: 0 });
  const addDeduction = () => add('deductions', { section: '80C', amount: 0, is_dependent: false, disability_certificate_available: false, specified_disease: false, donation_eligible: false, has_hra: false, owns_residential_property_at_residence_or_work: false, first_home_owner: false, loan_from_financial_institution: false, section_24b_limit_exhausted: false });
  const addBank = () => add('bank_accounts', { bank_name: '', account_number: '', ifsc_code: '', account_type: 'savings', is_primary: false });

  const handleFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files || []).map((file) => file.name);
    setFiles((current) => [...current, ...selected]);
    setFormData((current) => ({ ...current, documents: [...current.documents, ...selected.map((file_name) => ({ document_type: 'other' as const, file_name }))] }));
    event.target.value = '';
  };
  const removeFile = (index: number) => {
    setFiles((current) => current.filter((_, fileIndex) => fileIndex !== index));
    setFormData((current) => ({ ...current, documents: current.documents.filter((_, fileIndex) => fileIndex !== index) }));
  };
  const saveProfile = async () => {
    setSaving(true);
    setError('');
    try {
      const response = formData.id ? await taxProfileAPI.update(formData.id, formData) : await taxProfileAPI.create(formData);
      setFormData({ ...blankProfile, ...response.data });
      hydrated.current = true;
      setAssistantMessages((current) => [...current, 'Your profile is saved. You can keep editing it here.']);
    } catch (err: any) {
      setError(apiErrorMessage(err, 'Could not save your tax profile. Complete the required fields in the section you added.'));
    } finally {
      setSaving(false);
    }
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    await saveProfile();
  };
  const saveAssistantMessage = (message: string) => setAssistantMessages((current) => [...current, message]);
  const sendAssistantMessage = async () => {
    const question = assistantInput.trim();
    if (!question) return;
    saveAssistantMessage(`You: ${question}`);
    setAssistantInput('');
    try {
      const response = await onboardingAPI.sendMessage(question);
      setAssistantMessages((current) => [...current, response.data.assistant_message]);
      setProgress(response.data.progress);
      if (response.data.requires_confirmation) {
        const values = response.data.candidate_values;
        setProposal({ salary: values.salary_income?.[0]?.gross_salary ?? undefined, tds: values.salary_tds ?? undefined });
      }
    } catch (err: any) {
      setError(apiErrorMessage(err, 'The assistant could not process that answer.'));
    }
  };
  const confirmProposal = async () => {
    try {
      const response = await onboardingAPI.confirm('confirm');
      setAssistantMessages((current) => [...current, response.data.assistant_message]);
      setProgress(response.data.progress);
      if (response.data.profile) setFormData({ ...blankProfile, ...response.data.profile });
    } catch (err: any) {
      setError(apiErrorMessage(err, 'Could not save the proposed profile update.'));
      return;
    }
    setProposal(null);
  };
  const rejectProposal = async () => {
    await onboardingAPI.confirm('reject');
    setProposal(null);
    saveAssistantMessage('No changes made. Let\'s continue with the next question.');
  };
  const steps = ['About you', 'Residence & return', 'Income sources', 'Deductions', 'Taxes & banks', 'Documents'];
  const returnFlags: [string, string][] = [['is_senior_citizen','Senior citizen'],['is_director','Company director'],['has_unlisted_equity','Unlisted shares'],['has_business_income','Business or professional income'],['has_speculative_income','Speculative income'],['has_carry_forward_loss','Loss to carry forward']];
  const field = (name: string, label: string, type = 'text') => <label className="block text-sm text-gray-700">{label}<input className={inputClass} name={name} type={type} value={(formData as any)[name] ?? ''} onChange={update} /></label>;
  const listEditor = (key: keyof TaxProfile, title: string, addLabel: string, onAdd: () => void, fields: { name: string; label: string; type?: string }[]) => <section className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-semibold text-gray-900">{title}</h3><button type="button" onClick={onAdd} className="text-sm font-medium text-primary">+ {addLabel}</button></div>{(formData[key] as any[]).map((entry, index) => <div key={index} className="rounded-md border border-gray-200 p-4"><div className="grid gap-3 sm:grid-cols-2">{fields.map((item) => item.type === 'checkbox' ? <label key={item.name} className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={Boolean(entry[item.name])} onChange={(event) => updateEntry(key, index, item.name, event.target.checked)} />{item.label}</label> : <label key={item.name} className="text-sm text-gray-700">{item.label}<input className={inputClass} type={item.type || 'text'} value={entry[item.name] ?? ''} onChange={(event) => updateEntry(key, index, item.name, item.type === 'number' ? Number(event.target.value) : event.target.value)} /></label>)}</div><button type="button" onClick={() => remove(key, index)} className="mt-3 text-xs text-red-600">Remove</button></div>)}</section>;

  const handleAssistantPdf = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setDocumentProcessing(true);
    try {
      saveAssistantMessage(`PDF uploaded: ${file.name}. Processing...`);
      const uploaded = await documentsAPI.upload(file, formData.assessment_year);
      const processed = await documentsAPI.process(uploaded.data.id);
      await onboardingAPI.documentCandidate(processed.data.onboarding_values);
      const candidateSummary = processed.data.candidates.map((candidate: { field: string; value: string }) => `${candidate.field.replace('deduction_', '')}: ${candidate.value}`).join(' | ');
      setDocumentCandidates(processed.data.candidates);
      setProposal({ salary: processed.data.onboarding_values.salary_income?.[0]?.gross_salary, tds: processed.data.onboarding_values.salary_tds });
      saveAssistantMessage(processed.data.candidates.length ? 'Document processed. I found information for your review.' : 'Document processed, but no supported tax fields were found.');
      if (candidateSummary) saveAssistantMessage(candidateSummary);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      saveAssistantMessage(detail === 'DOCUMENT_REQUIRES_OCR' ? 'This PDF appears to be scanned. OCR is not available yet, so you can continue manually.' : 'I couldn\'t extract information from this document. You can continue manually.');
      setError(detail && detail !== 'DOCUMENT_REQUIRES_OCR' ? apiErrorMessage(err, '') : '');
    } finally {
      setDocumentProcessing(false);
    }
  };

  const confirmDocumentCandidates = async () => {
    if (!documentCandidates) return;
    const values: Record<string, unknown> = {};
    const salary = documentCandidates.find((item) => item.field === 'salary_income');
    const tds = documentCandidates.find((item) => item.field === 'tds');
    const employer = documentCandidates.find((item) => item.field === 'employer_name');
    const pan = documentCandidates.find((item) => item.field === 'pan_number');
    if (salary) values.salary_income = [{ employer_name: employer?.value || 'Document employer', gross_salary: Number(salary.value), standard_deduction: 0, professional_tax: 0, tds: 0 }];
    if (tds) values.salary_tds = Number(tds.value);
    if (employer) values.employer_name = employer.value;
    if (pan) values.pan_number = pan.value;
    const deductions = documentCandidates.filter((item) => item.field === 'deduction_80C' || item.field === 'deduction_80D').map((item) => ({ section: item.field.replace('deduction_', ''), amount: Number(item.value) }));
    if (deductions.length) values.deductions = deductions;
    try {
      await onboardingAPI.documentCandidate(values);
      const response = await onboardingAPI.confirm('confirm');
      if (response.data.profile) setFormData({ ...blankProfile, ...response.data.profile });
      setProgress(response.data.progress);
      setAssistantMessages((current) => [...current, "I've filled in the confirmed values from your document. Let's continue with the next missing field."]);
      setDocumentCandidates(null);
    } catch (err: any) {
      setError(apiErrorMessage(err, 'Could not confirm document values.'));
    }
  };

  return <div className="min-h-screen bg-gray-100 px-4 py-6 lg:px-6"><div className="mx-auto max-w-7xl"><header className="mb-6"><p className="text-sm font-semibold uppercase tracking-wide text-primary">TaxWise profile workspace</p><h1 className="mt-2 text-3xl font-bold text-gray-900">Your AY 2026-27 tax profile</h1><p className="mt-2 text-gray-600">Edit your profile on the left or use the assistant on the right. Both panels use the same saved profile.</p><div className="mt-4 h-2 overflow-hidden rounded-full bg-gray-200"><div className="h-full bg-primary transition-all" style={{ width: `${progress.percent}%` }} /></div><p className="mt-1 text-xs text-gray-500">{progress.completed} of {progress.total} sections completed</p></header><div className="grid items-start gap-6 lg:grid-cols-[1.22fr_1fr]"><section className="min-w-0 lg:max-h-[calc(100vh-150px)] lg:overflow-y-auto lg:pr-2"><div className="mb-6 grid grid-cols-3 gap-2 sm:grid-cols-6">{steps.map((name, index) => <button type="button" key={name} onClick={() => setStep(index + 1)} className={`border-b-4 px-1 py-2 text-xs ${step === index + 1 ? 'border-primary font-semibold text-primary' : 'border-gray-300 text-gray-500'}`}>{index + 1}. {name}</button>)}</div><form onSubmit={submit} className="space-y-6 rounded-lg bg-white p-6 shadow">
    {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {step === 1 && <div className="space-y-4"><h2 className="text-xl font-semibold">About you</h2><div className="grid gap-4 sm:grid-cols-2">{field('date_of_birth', 'Date of birth', 'date')}{field('pan_number', 'PAN (10 characters)')}{field('citizenship', 'Citizenship')}{field('nationality', 'Nationality')}{field('pincode', 'PIN code')}{field('city', 'City')}</div>{field('address', 'Residential address')}<div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-gray-700">Gender<select className={inputClass} name="gender" value={formData.gender || ''} onChange={update}><option value="">Choose</option><option>male</option><option>female</option><option>other</option></select></label><label className="text-sm text-gray-700">Marital status<select className={inputClass} name="marital_status" value={formData.marital_status || ''} onChange={update}><option value="">Choose</option><option>single</option><option>married</option><option>divorced</option><option>widowed</option></select></label></div></div>}
    {step === 2 && <div className="space-y-4"><h2 className="text-xl font-semibold">Residence and return details</h2><p className="text-sm text-gray-600">These answers help the future return selector understand your situation. They do not select an ITR yet.</p><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-gray-700">Residential status<select className={inputClass} name="residential_status" value={formData.residential_status} onChange={update}><option value="resident">Resident</option><option value="non_resident">Non-resident</option><option value="nri">NRI</option></select></label><label className="text-sm text-gray-700">Work situation<select className={inputClass} name="employment_type" value={formData.employment_type} onChange={update}><option value="salaried">Salaried</option><option value="self_employed">Self-employed</option><option value="both">Both</option><option value="none">Not working</option></select></label>{field('employer_name', 'Employer or organisation')}{field('assessment_year', 'Assessment year')}</div><div className="grid gap-3 sm:grid-cols-2">{returnFlags.map(([name, label]) => <label key={name} className="flex gap-2 text-sm"><input type="checkbox" name={name} checked={(formData as any)[name]} onChange={update} />{label}</label>)}</div></div>}
    {step === 3 && <div className="space-y-6"><h2 className="text-xl font-semibold">Income sources</h2>{listEditor('salary_income','Salary','salary',addSalary,[{name:'employer_name',label:'Employer'},{name:'gross_salary',label:'Annual gross salary',type:'number'},{name:'tds',label:'TDS shown on Form 16',type:'number'}])}{listEditor('pension_income','Pension','pension',addPension,[{name:'payer_name',label:'Pension payer'},{name:'amount',label:'Annual pension',type:'number'},{name:'tds',label:'TDS',type:'number'}])}{listEditor('house_properties','House property','property',addProperty,[{name:'property_type',label:'Type: self_occupied, let_out, or deemed_let_out'},{name:'city',label:'Property city'},{name:'annual_rent',label:'Annual rent',type:'number'},{name:'municipal_tax',label:'Municipal taxes paid',type:'number'},{name:'home_loan_interest',label:'Home-loan interest',type:'number'},{name:'loan_purpose',label:'Loan purpose: purchase_or_construction or repair'},{name:'loan_sanction_date',label:'Loan sanction date',type:'date'},{name:'construction_completed_within_five_years',label:'Construction completed within five years',type:'checkbox'}])}{listEditor('other_income','Interest, dividends and other income','income source',addOther,[{name:'description',label:'Description'},{name:'amount',label:'Amount',type:'number'},{name:'tds',label:'TDS',type:'number'}])}{listEditor('capital_gains','Capital gains','capital gain',addCapitalGain,[{name:'asset_type',label:'Asset type'},{name:'sale_value',label:'Sale value',type:'number'},{name:'cost_of_acquisition',label:'Purchase cost',type:'number'},{name:'gain_or_loss',label:'Gain or loss',type:'number'}])}{formData.has_business_income && listEditor('business_income','Business or professional income','business',addBusiness,[{name:'business_name',label:'Business name'},{name:'nature_of_business',label:'Nature of work'},{name:'gross_receipts',label:'Gross receipts',type:'number'},{name:'net_profit_or_loss',label:'Net profit or loss',type:'number'}])}{(formData.has_foreign_income || formData.has_foreign_assets) && listEditor('foreign_income_assets','Foreign income or assets','foreign item',addForeign,[{name:'country',label:'Country'},{name:'item_type',label:'Income or asset type'},{name:'description',label:'Description'},{name:'value',label:'Value',type:'number'}])}</div>}
    {step === 4 && <div className="space-y-6"><h2 className="text-xl font-semibold">Investments and deductions</h2><p className="text-sm text-gray-600">Enter the supporting facts for complex claims. TaxWise rejects a calculation if statutory facts or evidence details are missing.</p>{listEditor('investments','Investments','investment',addInvestment,[{name:'investment_type',label:'Type (for example, PPF)'},{name:'amount',label:'Amount',type:'number'}])}{listEditor('deductions','Deductions','deduction',addDeduction,[{name:'section',label:'Section (for example, 80C)'},{name:'amount',label:'Eligible payment or interest',type:'number'},{name:'dependent_relationship',label:'Dependent relationship (80DD/80DDB)'},{name:'dependent_age_category',label:'Patient age: individual, senior, super_senior'},{name:'disability_percentage',label:'Disability percentage',type:'number'},{name:'medical_expenditure',label:'Medical or maintenance expenditure',type:'number'},{name:'reimbursement_amount',label:'Reimbursement or insurance amount',type:'number'},{name:'donation_category',label:'80G category'},{name:'donation_mode',label:'80G payment: cash or non_cash'},{name:'form_10ba_acknowledgement',label:'80GG Form 10BA acknowledgement'},{name:'annual_rent',label:'80GG annual rent',type:'number'},{name:'loan_sanction_date',label:'80EE/80EEA sanction date',type:'date'},{name:'loan_amount',label:'80EE/80EEA loan amount',type:'number'},{name:'property_stamp_duty_value',label:'80EE/80EEA stamp-duty value',type:'number'},{name:'is_dependent',label:'Patient is a dependent',type:'checkbox'},{name:'disability_certificate_available',label:'Disability certificate available',type:'checkbox'},{name:'specified_disease',label:'Specified disease certified',type:'checkbox'},{name:'donation_eligible',label:'Donee is 80G eligible',type:'checkbox'},{name:'has_hra',label:'HRA received',type:'checkbox'},{name:'owns_residential_property_at_residence_or_work',label:'Owns residence/work-location property',type:'checkbox'},{name:'first_home_owner',label:'First-home condition met',type:'checkbox'},{name:'loan_from_financial_institution',label:'Loan from financial institution',type:'checkbox'},{name:'section_24b_limit_exhausted',label:'Section 24(b) limit exhausted (80EEA)',type:'checkbox'}])}</div>}
    {step === 5 && <div className="space-y-6"><h2 className="text-xl font-semibold">Taxes paid and bank accounts</h2><p className="text-sm text-gray-600">Bank details are used for refund processing. Account numbers are masked in API responses.</p>{listEditor('taxes_paid','TDS, advance tax and self-assessment tax','tax payment',addTax,[{name:'tax_type',label:'Payment type'},{name:'amount',label:'Amount',type:'number'},{name:'reference',label:'Challan or reference'}])}{listEditor('bank_accounts','Bank accounts','account',addBank,[{name:'bank_name',label:'Bank name'},{name:'account_number',label:'Account number'},{name:'ifsc_code',label:'IFSC code'}])}</div>}
    {step === 6 && <div className="space-y-4"><h2 className="text-xl font-semibold">Your documents</h2><p className="text-sm text-gray-600">Upload documents voluntarily from your device. TaxWise does not fetch documents from the Income Tax Department or your bank.</p><input type="file" multiple accept=".pdf,.jpg,.jpeg,.png" onChange={handleFiles} className="block w-full text-sm" />{files.length > 0 && <ul className="space-y-2 text-sm text-gray-700">{files.map((file, index) => <li key={`${file}-${index}`} className="flex items-center justify-between gap-3 rounded border border-gray-200 px-3 py-2"><span className="truncate">{file}</span><button type="button" onClick={() => removeFile(index)} className="shrink-0 text-xs font-medium text-red-600">Remove</button></li>)}</ul>}</div>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-6"><button type="button" disabled={step === 1} onClick={() => setStep(step - 1)} className="rounded-md border px-4 py-2 text-sm disabled:opacity-40">Previous</button><div className="flex gap-2"><button type="submit" disabled={saving} className="rounded-md border border-primary px-4 py-2 text-sm font-medium text-primary disabled:opacity-50">{saving ? 'Saving...' : 'Save progress'}</button>{step < 6 && <button type="button" onClick={() => setStep(step + 1)} className="rounded-md bg-primary px-4 py-2 text-sm text-white">Next</button>}</div></div>
  </form></section><aside className="flex min-h-[520px] flex-col rounded-lg bg-slate-900 p-5 text-white shadow lg:sticky lg:top-6 lg:max-h-[calc(100vh-48px)]"><div className="border-b border-slate-700 pb-4"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">TaxWise assistant</p><h2 className="mt-2 text-2xl font-semibold">Let’s fill this together</h2><p className="mt-2 text-sm text-slate-300">I can propose profile updates for your review. I do not calculate tax.</p></div><div className="flex-1 space-y-3 overflow-y-auto py-5" aria-live="polite">{assistantMessages.map((message, index) => <p key={`${message}-${index}`} className={`max-w-[92%] rounded-lg px-3 py-2 text-sm ${message.startsWith('You:') ? 'ml-auto bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-200'}`}>{message}</p>)}{proposal && <div className="rounded-lg border border-cyan-400/50 bg-slate-800 p-4 text-sm"><p className="font-semibold text-cyan-300">Proposed profile update</p>{proposal.salary !== undefined && <p className="mt-2">Salary: ₹{proposal.salary.toLocaleString('en-IN')}</p>}{proposal.tds !== undefined && <p>TDS: ₹{proposal.tds.toLocaleString('en-IN')}</p>}<div className="mt-4 flex gap-2"><button type="button" onClick={confirmProposal} className="rounded-md bg-cyan-400 px-3 py-2 font-medium text-slate-950">Add to profile</button><button type="button" onClick={() => setProposal(null)} className="rounded-md border border-slate-500 px-3 py-2">Review first</button></div></div>}</div><div className="border-t border-slate-700 pt-4"><div className="flex gap-2"><input value={assistantInput} onChange={(event) => setAssistantInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') sendAssistantMessage(); }} placeholder="Tell me about your income..." className="min-w-0 flex-1 rounded-md border-0 bg-white px-3 py-2 text-sm text-slate-900" /><button type="button" onClick={sendAssistantMessage} className="rounded-md bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950">Send</button></div><label className="mt-3 block text-xs text-slate-400">Have a tax document? <input type="file" accept="application/pdf" className="mt-1 block w-full text-xs text-slate-300" onChange={handleAssistantPdf} /></label></div></aside></div></div></div>;
};
export default TaxProfilePage;
