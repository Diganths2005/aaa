import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/store/auth';
import { documentsAPI, taxProfileAPI } from '@/lib/api';
import { TaxProfile } from '@/types';
import ReturnToDashboard from '@/components/ReturnToDashboard';
import FactReadinessPanel from '@/components/FactReadinessPanel';
import { getProfileCompletion } from '@/lib/profile-completion';

const inputClass = 'mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm transition focus:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-400/20';
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
  residential_status: '', employment_type: '', financial_year: '2025-26', assessment_year: '2026-27',
  salary_income: [], pension_income: [], house_properties: [], other_income: [], capital_gains: [], business_income: [],
  foreign_income_assets: [], investments: [], deductions: [], taxes_paid: [], bank_accounts: [], documents: [],
};

const TaxProfilePage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState<TaxProfile>(blankProfile);
  const [files, setFiles] = useState<Array<{ id: string; name: string }>>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [documentProcessing, setDocumentProcessing] = useState(false);
  const [progress, setProgress] = useState({ completed: 0, total: 16, percent: 0 });
  const hydrated = useRef(false);

  useEffect(() => { if (!isAuthenticated) router.push('/login'); }, [isAuthenticated, router]);
  useEffect(() => {
    if (!router.isReady || typeof router.query.section !== 'string') return;
    const sectionStep: Record<string, number> = {
      personal: 1,
      employment: 2,
      'salary-pension': 3,
      'house-property': 3,
      'other-income': 3,
      'capital-gains': 3,
      deductions: 4,
      tds: 5,
      'advance-tax': 5,
      'self-assessment-tax': 5,
      'bank-accounts': 5,
      'tax-documents': 6,
      'ais-26as': 6,
      'itr-information': 2,
    };
    setStep(sectionStep[router.query.section] || 1);
  }, [router.isReady, router.query.section]);
  useEffect(() => {
    if (!isAuthenticated) return;
    taxProfileAPI.getCurrentUser().then((response) => {
      setFormData({ ...blankProfile, ...response.data });
      const status = getProfileCompletion(response.data);
      setProgress({ completed: Math.round(status.percent / 10), total: 10, percent: status.percent });
      hydrated.current = true;
    }).catch(() => { hydrated.current = true; });
  }, [isAuthenticated]);
  if (!isAuthenticated) return null;

  const update = (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = event.target;
    const decisionFlags = ['is_senior_citizen', 'is_director', 'has_unlisted_equity', 'has_foreign_assets', 'has_foreign_income', 'has_business_income', 'has_speculative_income', 'has_carry_forward_loss'];
    setFormData((current) => ({
      ...current,
      [name]: type === 'checkbox'
        ? (event.target as HTMLInputElement).checked
        : type === 'number'
          ? Number(value)
          : decisionFlags.includes(name) && value !== ''
            ? value === 'true'
            : value === '' && decisionFlags.includes(name)
              ? undefined
              : value,
    }));
  };
  const add = (key: keyof TaxProfile, value: object) => setFormData((current) => ({ ...current, [key]: [...(current[key] as object[]), value] }));
  const remove = (key: keyof TaxProfile, index: number) => setFormData((current) => ({ ...current, [key]: (current[key] as object[]).filter((_, itemIndex) => itemIndex !== index) }));
  const updateEntry = (key: keyof TaxProfile, index: number, field: string, value: string | number | boolean | undefined) => setFormData((current) => ({ ...current, [key]: (current[key] as object[]).map((item, itemIndex) => itemIndex === index ? { ...item, [field]: value } : item) }));

  const addSalary = () => add('salary_income', { employer_name: '', gross_salary: 0, standard_deduction: 0, professional_tax: 0, tds: 0 });
  const addProperty = () => add('house_properties', { property_type: 'self_occupied', city: '', annual_rent: 0, municipal_tax: 0, home_loan_interest: 0, ownership_share: 100, loan_purpose: 'purchase_or_construction', loan_sanction_date: '', construction_completed_within_five_years: false });
  const addOther = () => add('other_income', { income_type: 'interest', description: '', amount: 0, tds: 0 });
  const addPension = () => add('pension_income', { payer_name: '', amount: 0, tds: 0 });
  const addCapitalGain = () => add('capital_gains', { asset_type: 'listed_equity_share', sale_consideration: 0, acquisition_cost: 0, improvement_cost: 0, transfer_expenses: 0 });
  const addBusiness = () => add('business_income', { business_name: '', nature_of_business: '', gross_receipts: 0, net_profit_or_loss: 0 });
  const addForeign = () => add('foreign_income_assets', { country: '', item_type: 'income', description: '', value: 0 });
  const addTax = () => add('taxes_paid', { tax_type: 'tds', amount: 0, reference: '' });
  const addInvestment = () => add('investments', { investment_type: '', amount: 0 });
  const addDeduction = () => add('deductions', { section: '80C', amount: 0, is_dependent: false, disability_certificate_available: false, specified_disease: false, donation_eligible: false, has_hra: false, owns_residential_property_at_residence_or_work: false, first_home_owner: false, loan_from_financial_institution: false, section_24b_limit_exhausted: false });
  const addBank = () => add('bank_accounts', { bank_name: '', account_number: '', ifsc_code: '', account_type: 'savings', is_primary: false });

  const handleFiles = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setDocumentProcessing(true);
    try {
      const uploaded = await documentsAPI.upload(file, formData.assessment_year);
      const processed = await documentsAPI.process(uploaded.data.id);
      setFiles((current) => [...current, { id: uploaded.data.id, name: file.name }]);
      if (processed.data.candidates.length) {
        await router.push('/documents');
        return;
      }
      setError(`${file.name} was processed, but no supported tax fields were found.`);
    } catch (uploadError: any) {
      const detail = uploadError.response?.data?.detail;
      setError(detail === 'DOCUMENT_REQUIRES_OCR'
        ? 'No text was found and OCR could not run on this server. Upload a text-based PDF or enter the information manually.'
        : apiErrorMessage(uploadError, 'Could not upload or process this document.'));
    } finally {
      setDocumentProcessing(false);
    }
  };
  const removeFile = async (index: number) => {
    const document = files[index];
    if (!document) return;
    try {
      await documentsAPI.delete(document.id);
      setFiles((current) => current.filter((_, fileIndex) => fileIndex !== index));
    } catch (removeError: any) {
      setError(apiErrorMessage(removeError, 'Could not remove this document.'));
    }
  };
  const saveProfile = async () => {
    const requiredChoices = ['is_senior_citizen', 'is_director', 'has_unlisted_equity', 'has_foreign_assets', 'has_foreign_income', 'has_business_income', 'has_speculative_income', 'has_carry_forward_loss'] as const;
    if (!formData.residential_status || !formData.employment_type || requiredChoices.some((key) => formData[key] === undefined)) {
      setError('Choose a residential status, work situation, and Yes or No for each return eligibility question. These are not preselected so TaxWise does not assume personal tax facts.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const response = formData.id ? await taxProfileAPI.update(formData.id, formData) : await taxProfileAPI.create(formData);
      setFormData({ ...blankProfile, ...response.data });
      const status = getProfileCompletion(response.data);
      setProgress({ completed: Math.round(status.percent / 10), total: 10, percent: status.percent });
      hydrated.current = true;
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
  const steps = ['About you', 'Residence & return', 'Income sources', 'Deductions', 'Taxes & banks', 'Documents'];
  const returnFlags: [string, string][] = [['is_senior_citizen','Senior citizen'],['is_director','Company director'],['has_unlisted_equity','Unlisted shares'],['has_foreign_assets','Foreign assets'],['has_foreign_income','Foreign income'],['has_business_income','Business or professional income'],['has_speculative_income','Speculative income'],['has_carry_forward_loss','Loss to carry forward']];
  const capitalGainFields = [
    { name: 'asset_identifier', label: 'Security or property identifier' },
    { name: 'asset_type', label: 'Asset type', options: [
      { value: 'listed_equity_share', label: 'Listed equity share' },
      { value: 'equity_oriented_mutual_fund', label: 'Equity-oriented mutual fund' },
      { value: 'other_security', label: 'Other security' },
      { value: 'immovable_property', label: 'Immovable property' },
      { value: 'gold_or_other', label: 'Gold or other asset' },
    ] },
    { name: 'acquisition_date', label: 'Acquisition date', type: 'date' },
    { name: 'sale_date', label: 'Sale date', type: 'date' },
    { name: 'holding_period', label: 'Source-reported holding period' },
    { name: 'gain_type', label: 'Source-reported gain type' },
    { name: 'sale_consideration', label: 'Sale consideration', type: 'number' },
    { name: 'acquisition_cost', label: 'Acquisition cost', type: 'number' },
    { name: 'improvement_cost', label: 'Improvement cost', type: 'number' },
    { name: 'transfer_expenses', label: 'Transfer expenses', type: 'number' },
    { name: 'quantity', label: 'Quantity (shares / units)', type: 'number' },
    { name: 'grandfathered_fmv_2018', label: 'FMV on 31 Jan 2018, if applicable', type: 'number' },
    { name: 'is_listed', label: 'Asset is listed', options: [{ value: true, label: 'Yes' }, { value: false, label: 'No' }] },
    { name: 'is_equity_oriented', label: 'Fund is equity-oriented', options: [{ value: true, label: 'Yes' }, { value: false, label: 'No' }] },
    { name: 'stt_paid_on_acquisition', label: 'STT paid on acquisition', options: [{ value: true, label: 'Yes' }, { value: false, label: 'No' }] },
    { name: 'stt_paid_on_transfer', label: 'STT paid on transfer', options: [{ value: true, label: 'Yes' }, { value: false, label: 'No' }] },
  ];
  const field = (name: string, label: string, type = 'text') => <label className="block text-sm text-gray-700">{label}<input className={inputClass} name={name} type={type} value={(formData as any)[name] ?? ''} onChange={update} /></label>;
  const listEditor = (key: keyof TaxProfile, title: string, addLabel: string, onAdd: () => void, fields: { name: string; label: string; type?: string; options?: { value: string | boolean; label: string }[] }[]) => {
    const visibleFields = key === 'capital_gains'
      ? capitalGainFields
      : key === 'deductions'
        ? [...fields, { name: 'donation_reference', label: '80G donation reference' }, { name: 'donation_ifsc', label: 'Donee bank IFSC' }]
        : fields;
    return (
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button type="button" onClick={onAdd} className="text-sm font-medium text-primary">+ {addLabel}</button>
        </div>
        {(formData[key] as any[]).map((entry, index) => (
          <div key={index} className="rounded-md border border-gray-200 p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              {visibleFields.map((item) => {
                if (item.type === 'checkbox') {
                  return <label key={item.name} className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" checked={Boolean(entry[item.name])} onChange={(event) => updateEntry(key, index, item.name, event.target.checked)} />{item.label}</label>;
                }
                if (item.options) {
                  return <label key={item.name} className="text-sm text-gray-700">{item.label}<select className={inputClass} value={entry[item.name] === undefined ? '' : String(entry[item.name])} onChange={(event) => { const selected = item.options?.find((option) => String(option.value) === event.target.value); updateEntry(key, index, item.name, selected?.value); }}><option value="">Select...</option>{item.options.map((option) => <option key={String(option.value)} value={String(option.value)}>{option.label}</option>)}</select></label>;
                }
                return <label key={item.name} className="text-sm text-gray-700">{item.label}<input className={inputClass} type={item.type || 'text'} value={entry[item.name] ?? ''} onChange={(event) => updateEntry(key, index, item.name, item.type === 'number' ? Number(event.target.value) : item.type === 'date' && event.target.value === '' ? undefined : event.target.value)} /></label>;
              })}
            </div>
            <button type="button" onClick={() => remove(key, index)} className="mt-3 text-xs text-red-600">Remove</button>
          </div>
        ))}
      </section>
    );
  };

  return <div className="page-shell"><div className="page-container"><header className="mb-8"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="section-kicker">TaxWise profile workspace</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">Your AY 2026-27 tax profile</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">Only information you enter or explicitly confirm is used for your personal tax calculations.</p></div><div className="flex flex-wrap gap-2"><ReturnToDashboard /><a href="/taxpayer-profile" className="rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50">Cancel</a></div></div><div className="mt-5 h-2.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${progress.percent}%` }} /></div><div className="mt-2 flex items-center justify-between"><p className="text-xs font-medium text-slate-500">Profile completion</p><p className="text-xs font-semibold text-emerald-700">{progress.percent}%</p></div><div className="mt-4 flex flex-wrap gap-2 text-xs"><span className="chip">User-provided / confirmed</span><span className="chip">Documents require review</span><span className="chip">Engine results stay separate</span></div></header><div className="space-y-6"><FactReadinessPanel /><section className="min-w-0"><div className="mb-5 grid grid-cols-3 gap-2 sm:grid-cols-6">{steps.map((name, index) => <button type="button" key={name} onClick={() => setStep(index + 1)} className={`rounded-xl border px-2.5 py-2.5 text-xs font-medium transition-all ${step === index + 1 ? 'border-emerald-200 bg-emerald-50 font-semibold text-emerald-800 shadow-sm' : 'border-slate-200 bg-white text-slate-500 hover:border-slate-300 hover:text-slate-700'}`}><span className="mr-1">{index + 1}.</span>{name}</button>)}</div><form onSubmit={submit} className="surface-panel space-y-6 p-5 sm:p-7">
    {error && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    {step === 1 && <div className="space-y-4"><h2 className="text-xl font-semibold">About you</h2><div className="grid gap-4 sm:grid-cols-2">{field('date_of_birth', 'Date of birth', 'date')}{field('pan_number', 'PAN (10 characters)')}{field('citizenship', 'Citizenship')}{field('nationality', 'Nationality')}{field('pincode', 'PIN code')}{field('city', 'City')}</div>{field('address', 'Residential address')}<div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-gray-700">Gender<select className={inputClass} name="gender" value={formData.gender || ''} onChange={update}><option value="">Choose</option><option>male</option><option>female</option><option>other</option></select></label><label className="text-sm text-gray-700">Marital status<select className={inputClass} name="marital_status" value={formData.marital_status || ''} onChange={update}><option value="">Choose</option><option>single</option><option>married</option><option>divorced</option><option>widowed</option></select></label></div></div>}
    {step === 2 && <div className="space-y-4"><h2 className="text-xl font-semibold">Residence and return details</h2><p className="text-sm text-gray-600">Choose these values explicitly. TaxWise does not assume a residency, employment situation, or return eligibility flag.</p><div className="grid gap-4 sm:grid-cols-2"><label className="text-sm text-gray-700">Residential status<select className={inputClass} name="residential_status" value={formData.residential_status} onChange={update}><option value="">Select residential status</option><option value="resident">Resident</option><option value="non_resident">Non-resident</option><option value="nri">NRI</option></select></label><label className="text-sm text-gray-700">Work situation<select className={inputClass} name="employment_type" value={formData.employment_type} onChange={update}><option value="">Select work situation</option><option value="salaried">Salaried</option><option value="self_employed">Self-employed</option><option value="both">Both</option><option value="none">Not working</option></select></label>{field('employer_name', 'Employer or organisation')}{field('assessment_year', 'Assessment year')}</div><div className="grid gap-3 sm:grid-cols-2">{returnFlags.map(([name, label]) => <label key={name} className="block text-sm text-gray-700">{label}<select className={inputClass} name={name} value={(formData as any)[name] === undefined ? '' : String((formData as any)[name])} onChange={update}><option value="">Select Yes or No</option><option value="true">Yes</option><option value="false">No</option></select></label>)}</div></div>}
    {step === 3 && <div className="space-y-6"><h2 className="text-xl font-semibold">Income sources</h2>{listEditor('salary_income','Salary','salary',addSalary,[{name:'employer_name',label:'Employer'},{name:'gross_salary',label:'Annual gross salary',type:'number'},{name:'tds',label:'TDS shown on Form 16',type:'number'}])}{listEditor('pension_income','Pension','pension',addPension,[{name:'payer_name',label:'Pension payer'},{name:'amount',label:'Annual pension',type:'number'},{name:'tds',label:'TDS',type:'number'}])}{listEditor('house_properties','House property','property',addProperty,[{name:'property_type',label:'Type: self_occupied, let_out, or deemed_let_out'},{name:'city',label:'Property city'},{name:'annual_rent',label:'Annual rent',type:'number'},{name:'municipal_tax',label:'Municipal taxes paid',type:'number'},{name:'home_loan_interest',label:'Home-loan interest',type:'number'},{name:'loan_purpose',label:'Loan purpose: purchase_or_construction or repair'},{name:'loan_sanction_date',label:'Loan sanction date',type:'date'},{name:'construction_completed_within_five_years',label:'Construction completed within five years',type:'checkbox'}])}{listEditor('other_income','Interest, dividends and other income','income source',addOther,[{name:'description',label:'Description'},{name:'amount',label:'Amount',type:'number'},{name:'tds',label:'TDS',type:'number'}])}{listEditor('capital_gains','Capital gains','capital gain',addCapitalGain,[{name:'asset_type',label:'Asset type'},{name:'sale_value',label:'Sale value',type:'number'},{name:'cost_of_acquisition',label:'Purchase cost',type:'number'},{name:'gain_or_loss',label:'Gain or loss',type:'number'}])}{formData.has_business_income && listEditor('business_income','Business or professional income','business',addBusiness,[{name:'business_name',label:'Business name'},{name:'nature_of_business',label:'Nature of work'},{name:'gross_receipts',label:'Gross receipts',type:'number'},{name:'net_profit_or_loss',label:'Net profit or loss',type:'number'}])}{(formData.has_foreign_income || formData.has_foreign_assets) && listEditor('foreign_income_assets','Foreign income or assets','foreign item',addForeign,[{name:'country',label:'Country'},{name:'item_type',label:'Income or asset type'},{name:'description',label:'Description'},{name:'value',label:'Value',type:'number'}])}</div>}
    {step === 4 && <div className="space-y-6"><h2 className="text-xl font-semibold">Investments and deductions</h2><p className="text-sm text-gray-600">Enter the supporting facts for complex claims. TaxWise rejects a calculation if statutory facts or evidence details are missing.</p>{listEditor('investments','Investments','investment',addInvestment,[{name:'investment_type',label:'Type (for example, PPF)'},{name:'amount',label:'Amount',type:'number'}])}{listEditor('deductions','Deductions','deduction',addDeduction,[{name:'section',label:'Section (for example, 80C)'},{name:'amount',label:'Eligible payment or interest',type:'number'},{name:'dependent_relationship',label:'Dependent relationship (80DD/80DDB)'},{name:'dependent_age_category',label:'Patient age: individual, senior, super_senior'},{name:'disability_percentage',label:'Disability percentage',type:'number'},{name:'medical_expenditure',label:'Medical or maintenance expenditure',type:'number'},{name:'reimbursement_amount',label:'Reimbursement or insurance amount',type:'number'},{name:'donation_category',label:'80G category'},{name:'donation_mode',label:'80G payment: cash or non_cash'},{name:'form_10ba_acknowledgement',label:'80GG Form 10BA acknowledgement'},{name:'annual_rent',label:'80GG annual rent',type:'number'},{name:'loan_sanction_date',label:'80EE/80EEA sanction date',type:'date'},{name:'loan_amount',label:'80EE/80EEA loan amount',type:'number'},{name:'property_stamp_duty_value',label:'80EE/80EEA stamp-duty value',type:'number'},{name:'is_dependent',label:'Patient is a dependent',type:'checkbox'},{name:'disability_certificate_available',label:'Disability certificate available',type:'checkbox'},{name:'specified_disease',label:'Specified disease certified',type:'checkbox'},{name:'donation_eligible',label:'Donee is 80G eligible',type:'checkbox'},{name:'has_hra',label:'HRA received',type:'checkbox'},{name:'owns_residential_property_at_residence_or_work',label:'Owns residence/work-location property',type:'checkbox'},{name:'first_home_owner',label:'First-home condition met',type:'checkbox'},{name:'loan_from_financial_institution',label:'Loan from financial institution',type:'checkbox'},{name:'section_24b_limit_exhausted',label:'Section 24(b) limit exhausted (80EEA)',type:'checkbox'}])}</div>}
    {step === 5 && <div className="space-y-6"><h2 className="text-xl font-semibold">Taxes paid and bank accounts</h2><p className="text-sm text-gray-600">Bank details are used for refund processing. Account numbers are masked in API responses.</p>{listEditor('taxes_paid','TDS, advance tax and self-assessment tax','tax payment',addTax,[{name:'tax_type',label:'Payment type'},{name:'amount',label:'Amount',type:'number'},{name:'reference',label:'Challan or reference'}])}{listEditor('bank_accounts','Bank accounts','account',addBank,[{name:'bank_name',label:'Bank name'},{name:'account_number',label:'Account number'},{name:'ifsc_code',label:'IFSC code'}])}</div>}
    {step === 6 && <div className="space-y-4"><h2 className="text-xl font-semibold">Your documents</h2><p className="text-sm text-gray-600">Upload a PDF or Excel workbook. TaxWise does not fetch documents from the Income Tax Department or your bank.</p><input type="file" accept="application/pdf,.xlsx,.xlsm" onChange={handleFiles} disabled={documentProcessing} className="block w-full text-sm" />{files.length > 0 && <ul className="space-y-2 text-sm text-gray-700">{files.map((file, index) => <li key={file.id} className="flex items-center justify-between gap-3 rounded border border-gray-200 px-3 py-2"><span className="truncate">{file.name}</span><button type="button" onClick={() => removeFile(index)} className="shrink-0 text-xs font-medium text-red-600">Remove</button></li>)}</ul>}</div>}
    <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-6"><button type="button" disabled={step === 1} onClick={() => setStep(step - 1)} className="rounded-md border px-4 py-2 text-sm disabled:opacity-40">Previous</button><div className="flex gap-2"><button type="submit" disabled={saving} className="rounded-md border border-primary px-4 py-2 text-sm font-medium text-primary disabled:opacity-50">{saving ? 'Saving...' : 'Save progress'}</button>{step < 6 && <button type="button" onClick={() => setStep(step + 1)} className="rounded-md bg-primary px-4 py-2 text-sm text-white">Next</button>}</div></div>
  </form></section></div></div></div>;
};
export default TaxProfilePage;
