import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/store/auth';
import { taxProfileAPI } from '@/lib/api';
import { TaxProfile } from '@/types';

const inputClass = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm';
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

  useEffect(() => { if (!isAuthenticated) router.push('/login'); }, [isAuthenticated, router]);
  if (!isAuthenticated) return null;

  const update = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = event.target;
    setFormData((current) => ({ ...current, [name]: type === 'checkbox' ? (event.target as HTMLInputElement).checked : type === 'number' ? Number(value) : value }));
  };
  const add = (key: keyof TaxProfile, value: object) => setFormData((current) => ({ ...current, [key]: [...(current[key] as object[]), value] }));
  const remove = (key: keyof TaxProfile, index: number) => setFormData((current) => ({ ...current, [key]: (current[key] as object[]).filter((_, itemIndex) => itemIndex !== index) }));
  const updateEntry = (key: keyof TaxProfile, index: number, field: string, value: string | number) => setFormData((current) => ({ ...current, [key]: (current[key] as object[]).map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item) }));

  const addSalary = () => add('salary_income', { employer_name: '', gross_salary: 0, standard_deduction: 0, professional_tax: 0, tds: 0 });
  const addProperty = () => add('house_properties', { property_type: 'self_occupied', city: '', annual_rent: 0, municipal_tax: 0, home_loan_interest: 0, ownership_share: 100 });
  const addOther = () => add('other_income', { income_type: 'interest', description: '', amount: 0, tds: 0 });
  const addPension = () => add('pension_income', { payer_name: '', amount: 0, tds: 0 });
  const addCapitalGain = () => add('capital_gains', { asset_type: 'equity', holding_period: 'short_term', sale_value: 0, cost_of_acquisition: 0, transfer_expenses: 0, gain_or_loss: 0 });
  const addBusiness = () => add('business_income', { business_name: '', nature_of_business: '', gross_receipts: 0, net_profit_or_loss: 0 });
  const addForeign = () => add('foreign_income_assets', { country: '', item_type: 'income', description: '', value: 0 });
  const addTax = () => add('taxes_paid', { tax_type: 'tds', amount: 0, reference: '' });
  const addInvestment = () => add('investments', { investment_type: '', amount: 0 });
  const addDeduction = () => add('deductions', { section: '80C', amount: 0 });
  const addBank = () => add('bank_accounts', { bank_name: '', account_number: '', ifsc_code: '', account_type: 'savings', is_primary: false });

  const handleFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files || []).map((file) => file.name);
    setFiles((current) => [...current, ...selected]);
    setFormData((current) => ({ ...current, documents: [...current.documents, ...selected.map((file_name) => ({ document_type: 'other' as const, file_name }))] }));
  };
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setSaving(true); setError('');
    try { await taxProfileAPI.create(formData); router.push('/dashboard'); }
    catch (err: any) { setError(err.response?.data?.detail || 'Could not save your tax profile.'); }
    finally { setSaving(false); }
  };
  const steps = ['About you', 'Residence & return', 'Income sources', 'Deductions', 'Taxes & banks', 'Documents'];
  const returnFlags: [string, string][] = [['is_senior_citizen','Senior citizen'],['is_director','Company director'],['has_unlisted_equity','Unlisted shares'],['has_business_income','Business or professional income'],['has_speculative_income','Speculative income'],['has_carry_forward_loss','Loss to carry forward']];
  const field = (name: string, label: string, type = 'text') => <label className="block text-sm text-gray-700">{label}<input className={inputClass} name={name} type={type} value={(formData as any)[name] ?? ''} onChange={update} /></label>;
  const listEditor = (key: keyof TaxProfile, title: string, addLabel: string, onAdd: () => void, fields: { name: string; label: string; type?: string }[]) => <section className="space-y-3"><div className="flex items-center justify-between"><h3 className="font-semibold text-gray-900">{title}</h3><button type="button" onClick={onAdd} className="text-sm font-medium text-primary">+ {addLabel}</button></div>{(formData[key] as any[]).map((entry, index) => <div key={index} className="rounded-md border border-gray-200 p-4"><div className="grid gap-3 sm:grid-cols-2">{fields.map((item) => <label key={item.name} className="text-sm text-gray-700">{item.label}<input className={inputClass} type={item.type || 'text'} value={entry[item.name]} onChange={(event) => updateEntry(key, index, item.name, item.type === 'number' ? Number(event.target.value) : event.target.value)} /></label>)}</div><button type="button" onClick={() => remove(key, index)} className="mt-3 text-xs text-red-600">Remove</button></div>)}</section>;

  return <div className="min-h-screen bg-gray-100 px-4 py-10"><div className="mx-auto max-w-4xl"><header className="mb-8"><p className="text-sm font-semibold uppercase tracking-wide text-primary">TaxWise profile</p><h1 className="mt-2 text-3xl font-bold text-gray-900">Your AY 2026-27 tax profile</h1><p className="mt-2 text-gray-600">This information prepares your profile for ITR-1 through ITR-4. You can review it before filing.</p></header><div className="mb-6 grid grid-cols-3 gap-2 sm:grid-cols-6">{steps.map((name, index) => <button type="button" key={name} onClick={() => setStep(index + 1)} className={`border-b-4 px-1 py-2 text-xs ${step === index + 1 ? 'border-primary font-semibold text-primary' : 'border-gray-300 text-gray-500'}`}>{index + 1}. {name}</button>)}</div><form onSubmit={submit} className="space-y-6 rounded-lg bg-white p-6 shadow">
    {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {step === 1 && <div className="space-y-4"><h2 className="text-xl font-semibold">About you</h2><div className="grid gap-4 sm:grid-cols-2">{field('date_of_birth', 'Date of birth', 'date')}{field('pan_number', 'PAN (10 characters)')}{field('citizenship', 'Citizenship')}{field('nationality', 'Nationality')}{field('pincode', 'PIN code')}{field('city', 'City')}</div>{field('address', 'Residential address')}<div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-gray-700">Gender<select className={inputClass} name="gender" value={formData.gender || ''} onChange={update}><option value="">Choose</option><option>male</option><option>female</option><option>other</option></select></label><label className="text-sm text-gray-700">Marital status<select className={inputClass} name="marital_status" value={formData.marital_status || ''} onChange={update}><option value="">Choose</option><option>single</option><option>married</option><option>divorced</option><option>widowed</option></select></label></div></div>}
    {step === 2 && <div className="space-y-4"><h2 className="text-xl font-semibold">Residence and return details</h2><p className="text-sm text-gray-600">These answers help the future return selector understand your situation. They do not select an ITR yet.</p><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-gray-700">Residential status<select className={inputClass} name="residential_status" value={formData.residential_status} onChange={update}><option value="resident">Resident</option><option value="non_resident">Non-resident</option><option value="nri">NRI</option></select></label><label className="text-sm text-gray-700">Work situation<select className={inputClass} name="employment_type" value={formData.employment_type} onChange={update}><option value="salaried">Salaried</option><option value="self_employed">Self-employed</option><option value="both">Both</option><option value="none">Not working</option></select></label>{field('employer_name', 'Employer or organisation')}{field('assessment_year', 'Assessment year')}</div><div className="grid gap-3 sm:grid-cols-2">{returnFlags.map(([name, label]) => <label key={name} className="flex gap-2 text-sm"><input type="checkbox" name={name} checked={(formData as any)[name]} onChange={update} />{label}</label>)}</div></div>}
    {step === 3 && <div className="space-y-6"><h2 className="text-xl font-semibold">Income sources</h2>{listEditor('salary_income','Salary','salary',addSalary,[{name:'employer_name',label:'Employer'},{name:'gross_salary',label:'Annual gross salary',type:'number'},{name:'tds',label:'TDS shown on Form 16',type:'number'}])}{listEditor('pension_income','Pension','pension',addPension,[{name:'payer_name',label:'Pension payer'},{name:'amount',label:'Annual pension',type:'number'},{name:'tds',label:'TDS',type:'number'}])}{listEditor('house_properties','House property','property',addProperty,[{name:'city',label:'Property city'},{name:'annual_rent',label:'Annual rent',type:'number'},{name:'home_loan_interest',label:'Home-loan interest',type:'number'}])}{listEditor('other_income','Interest, dividends and other income','income source',addOther,[{name:'description',label:'Description'},{name:'amount',label:'Amount',type:'number'},{name:'tds',label:'TDS',type:'number'}])}{listEditor('capital_gains','Capital gains','capital gain',addCapitalGain,[{name:'asset_type',label:'Asset type'},{name:'sale_value',label:'Sale value',type:'number'},{name:'cost_of_acquisition',label:'Purchase cost',type:'number'},{name:'gain_or_loss',label:'Gain or loss',type:'number'}])}{formData.has_business_income && listEditor('business_income','Business or professional income','business',addBusiness,[{name:'business_name',label:'Business name'},{name:'nature_of_business',label:'Nature of work'},{name:'gross_receipts',label:'Gross receipts',type:'number'},{name:'net_profit_or_loss',label:'Net profit or loss',type:'number'}])}{(formData.has_foreign_income || formData.has_foreign_assets) && listEditor('foreign_income_assets','Foreign income or assets','foreign item',addForeign,[{name:'country',label:'Country'},{name:'item_type',label:'Income or asset type'},{name:'description',label:'Description'},{name:'value',label:'Value',type:'number'}])}</div>}
    {step === 4 && <div className="space-y-6"><h2 className="text-xl font-semibold">Investments and deductions</h2><p className="text-sm text-gray-600">Add each eligible investment or deduction separately. Keep receipts for review.</p>{listEditor('investments','Investments','investment',addInvestment,[{name:'investment_type',label:'Type (for example, PPF)'},{name:'amount',label:'Amount',type:'number'}])}{listEditor('deductions','Deductions','deduction',addDeduction,[{name:'section',label:'Section (for example, 80C)'},{name:'amount',label:'Amount',type:'number'}])}</div>}
    {step === 5 && <div className="space-y-6"><h2 className="text-xl font-semibold">Taxes paid and bank accounts</h2><p className="text-sm text-gray-600">Bank details are used for refund processing. Account numbers are masked in API responses.</p>{listEditor('taxes_paid','TDS, advance tax and self-assessment tax','tax payment',addTax,[{name:'tax_type',label:'Payment type'},{name:'amount',label:'Amount',type:'number'},{name:'reference',label:'Challan or reference'}])}{listEditor('bank_accounts','Bank accounts','account',addBank,[{name:'bank_name',label:'Bank name'},{name:'account_number',label:'Account number'},{name:'ifsc_code',label:'IFSC code'}])}</div>}
    {step === 6 && <div className="space-y-4"><h2 className="text-xl font-semibold">Your documents</h2><p className="text-sm text-gray-600">Upload documents voluntarily from your device. TaxWise does not fetch documents from the Income Tax Department or your bank.</p><input type="file" multiple accept=".pdf,.jpg,.jpeg,.png" onChange={handleFiles} className="block w-full text-sm" />{files.length > 0 && <ul className="list-disc pl-5 text-sm text-gray-700">{files.map((file, index) => <li key={`${file}-${index}`}>{file}</li>)}</ul>}</div>}
    <div className="flex justify-between border-t pt-6"><button type="button" disabled={step === 1} onClick={() => setStep(step - 1)} className="rounded-md border px-4 py-2 text-sm disabled:opacity-40">Previous</button>{step < 6 ? <button type="button" onClick={() => setStep(step + 1)} className="rounded-md bg-primary px-4 py-2 text-sm text-white">Next</button> : <button type="submit" disabled={saving} className="rounded-md bg-primary px-4 py-2 text-sm text-white disabled:opacity-50">{saving ? 'Saving...' : 'Save profile'}</button>}</div>
  </form></div></div>;
};
export default TaxProfilePage;
