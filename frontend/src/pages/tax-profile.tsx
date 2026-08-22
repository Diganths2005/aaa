import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { useAuthStore } from '@/store/auth';
import { taxProfileAPI } from '@/lib/api';
import { TaxProfile } from '@/types';

const TaxProfilePage: React.FC = () => {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);

  const [formData, setFormData] = useState<Partial<TaxProfile>>({
    // Personal Information
    dateOfBirth: '',
    panNumber: '',
    aadhaarNumber: '',
    gender: '',
    maritalStatus: '',
    address: '',
    city: '',
    state: '',
    pincode: '',
    
    // Residential Status
    residentialStatus: 'resident',
    
    // Employment Information
    employmentType: 'salaried',
    salaryIncome: 0,
    employerName: '',
    employerAddress: '',
    
    // Other Income
    otherIncome: 0,
    otherIncomeType: '',
    
    // House Property
    housePropertyIncome: 0,
    propertyDescription: '',
    
    // Investments
    investments: [],
    
    // Deductions
    deductions: [],
    
    // TDS/Tax Paid
    tdsPaid: 0,
    advanceTaxPaid: 0,
    selfAssessmentTax: 0,
    
    // Bank Account
    bankName: '',
    accountNumber: '',
    ifscCode: '',
    accountType: 'savings',
  });

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    const finalValue = type === 'number' ? (value ? parseFloat(value) : 0) : value;
    
    setFormData((prev) => ({
      ...prev,
      [name]: finalValue,
    }));
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    
    const file = e.target.files[0];
    setIsLoading(true);
    setError('');

    try {
      // This will be implemented after creating the profile
      setUploadedDocs([...uploadedDocs, file.name]);
      alert(`File ${file.name} uploaded successfully`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await taxProfileAPI.create(formData);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create tax profile');
    } finally {
      setIsLoading(false);
    }
  };

  const steps = [
    { id: 1, name: 'Personal Info', fields: ['dateOfBirth', 'panNumber', 'aadhaarNumber', 'gender', 'maritalStatus', 'address', 'city', 'state', 'pincode'] },
    { id: 2, name: 'Residence & Employment', fields: ['residentialStatus', 'employmentType', 'salaryIncome', 'employerName', 'employerAddress'] },
    { id: 3, name: 'Income Details', fields: ['otherIncome', 'otherIncomeType', 'housePropertyIncome', 'propertyDescription'] },
    { id: 4, name: 'Investments & Deductions', fields: ['investments', 'deductions'] },
    { id: 5, name: 'Tax & Bank Details', fields: ['tdsPaid', 'advanceTaxPaid', 'selfAssessmentTax', 'bankName', 'accountNumber', 'ifscCode', 'accountType'] },
    { id: 6, name: 'Documents', fields: ['documents'] },
  ];

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Steps Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {steps.map((step) => (
              <div key={step.id} className="flex flex-col items-center flex-1">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold mb-2 ${
                    currentStep >= step.id
                      ? 'bg-primary text-white'
                      : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  {step.id}
                </div>
                <span className="text-xs text-center text-gray-600">{step.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-8">
          {error && (
            <div className="mb-6 rounded-md bg-red-50 p-4">
              <p className="text-sm font-medium text-red-800">{error}</p>
            </div>
          )}

          {/* Step 1: Personal Information */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Personal Information</h2>
              
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <input type="date" name="dateOfBirth" placeholder="Date of Birth" value={formData.dateOfBirth} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <input type="text" name="panNumber" placeholder="PAN Number" value={formData.panNumber} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <input type="text" name="aadhaarNumber" placeholder="Aadhaar Number" value={formData.aadhaarNumber} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <select name="gender" value={formData.gender} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm">
                  <option value="">Select Gender</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
                <select name="maritalStatus" value={formData.maritalStatus} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm">
                  <option value="">Select Marital Status</option>
                  <option value="single">Single</option>
                  <option value="married">Married</option>
                  <option value="divorced">Divorced</option>
                  <option value="widowed">Widowed</option>
                </select>
              </div>

              <textarea name="address" placeholder="Address" value={formData.address} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" rows={2} />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <input type="text" name="city" placeholder="City" value={formData.city} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <input type="text" name="state" placeholder="State" value={formData.state} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <input type="text" name="pincode" placeholder="Pincode" value={formData.pincode} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
              </div>
            </div>
          )}

          {/* Step 2: Residence & Employment */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Residential Status & Employment</h2>
              
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <select name="residentialStatus" value={formData.residentialStatus} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm">
                  <option value="resident">Resident</option>
                  <option value="non_resident">Non-Resident</option>
                  <option value="nri">NRI</option>
                </select>
                <select name="employmentType" value={formData.employmentType} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm">
                  <option value="salaried">Salaried</option>
                  <option value="self_employed">Self Employed</option>
                  <option value="both">Both</option>
                  <option value="none">None</option>
                </select>
              </div>

              <input type="number" name="salaryIncome" placeholder="Salary Income" value={formData.salaryIncome} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <input type="text" name="employerName" placeholder="Employer Name" value={formData.employerName} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <textarea name="employerAddress" placeholder="Employer Address" value={formData.employerAddress} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" rows={2} />
            </div>
          )}

          {/* Step 3: Income Details */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Income Details</h2>
              
              <input type="number" name="otherIncome" placeholder="Other Income Amount" value={formData.otherIncome} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <input type="text" name="otherIncomeType" placeholder="Other Income Type" value={formData.otherIncomeType} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <input type="number" name="housePropertyIncome" placeholder="House Property Income" value={formData.housePropertyIncome} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <textarea name="propertyDescription" placeholder="Property Description" value={formData.propertyDescription} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" rows={2} />
            </div>
          )}

          {/* Step 4: Investments & Deductions */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Investments & Deductions</h2>
              <p className="text-sm text-gray-600 mb-4">Add your investments and deductions details here. You can add multiple entries.</p>
              <div className="bg-blue-50 p-4 rounded-md text-sm text-blue-800">
                Note: The investment and deduction form will be dynamically generated in the next phase.
              </div>
            </div>
          )}

          {/* Step 5: Tax & Bank Details */}
          {currentStep === 5 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Tax & Bank Details</h2>
              
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <input type="number" name="tdsPaid" placeholder="TDS Paid" value={formData.tdsPaid} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <input type="number" name="advanceTaxPaid" placeholder="Advance Tax Paid" value={formData.advanceTaxPaid} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
                <input type="number" name="selfAssessmentTax" placeholder="Self Assessment Tax" value={formData.selfAssessmentTax} onChange={handleInputChange} className="px-3 py-2 border border-gray-300 rounded-md text-sm" />
              </div>

              <input type="text" name="bankName" placeholder="Bank Name" value={formData.bankName} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <input type="text" name="accountNumber" placeholder="Account Number" value={formData.accountNumber} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <input type="text" name="ifscCode" placeholder="IFSC Code" value={formData.ifscCode} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm" />
              <select name="accountType" value={formData.accountType} onChange={handleInputChange} className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm">
                <option value="savings">Savings</option>
                <option value="current">Current</option>
                <option value="nri">NRI</option>
              </select>
            </div>
          )}

          {/* Step 6: Documents */}
          {currentStep === 6 && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Upload Documents</h2>
              
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                <input
                  type="file"
                  id="fileUpload"
                  onChange={handleFileUpload}
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png"
                />
                <label htmlFor="fileUpload" className="cursor-pointer">
                  <div className="text-4xl mb-2">📎</div>
                  <p className="text-gray-600">Click to upload or drag and drop</p>
                  <p className="text-sm text-gray-500">PDF, JPG, PNG up to 10MB</p>
                </label>
              </div>

              {uploadedDocs.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-medium text-gray-900 mb-2">Uploaded Files:</h3>
                  <ul className="space-y-2">
                    {uploadedDocs.map((doc, idx) => (
                      <li key={idx} className="text-sm text-gray-600">✓ {doc}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-8 pt-8 border-t">
            <button
              type="button"
              onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
              disabled={currentStep === 1}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>

            {currentStep === steps.length ? (
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? 'Saving...' : 'Complete & Save'}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setCurrentStep(currentStep + 1)}
                className="px-4 py-2 bg-primary text-white rounded-md hover:bg-blue-700"
              >
                Next
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default TaxProfilePage;
