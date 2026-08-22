export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  createdAt: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TaxProfile {
  id?: string;
  userId: string;
  // Personal Information
  dateOfBirth: string;
  panNumber: string;
  aadhaarNumber: string;
  gender: string;
  maritalStatus: string;
  address: string;
  city: string;
  state: string;
  pincode: string;
  
  // Residential Status
  residentialStatus: 'resident' | 'non_resident' | 'nri';
  
  // Employment Information
  employmentType: 'salaried' | 'self_employed' | 'both' | 'none';
  salaryIncome: number;
  employerName: string;
  employerAddress: string;
  
  // Other Income
  otherIncome: number;
  otherIncomeType: string;
  
  // House Property
  housePropertyIncome: number;
  propertyDescription: string;
  
  // Investments
  investments: {
    type: string;
    amount: number;
  }[];
  
  // Deductions
  deductions: {
    type: string;
    amount: number;
  }[];
  
  // TDS/Tax Paid
  tdsPaid: number;
  advanceTaxPaid: number;
  selfAssessmentTax: number;
  
  // Bank Account
  bankName: string;
  accountNumber: string;
  ifscCode: string;
  accountType: string;
  
  // Documents
  documents: {
    type: string;
    fileName: string;
    uploadedAt: string;
  }[];
  
  createdAt?: string;
  updatedAt?: string;
}

export interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, firstName: string, lastName: string, password: string) => Promise<void>;
  logout: () => void;
}
