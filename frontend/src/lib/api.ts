import axios, { AxiosInstance } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1_URL = `${API_URL}/api/v1`;

const sanitizeProfilePayload = <T extends Record<string, any>>(data: T): T => {
  const payload = { ...data };
  if (typeof payload.pan_number === 'string' && (payload.pan_number.includes('*') || /^\w{2}\*{6}\w{2}$/.test(payload.pan_number))) {
    delete payload.pan_number;
  }
  return payload;
};

const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle response errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  signup: (email: string, firstName: string, lastName: string, password: string) =>
    apiClient.post(`${API_V1_URL}/auth/signup`, { email, first_name: firstName, last_name: lastName, password }),
  
  login: (email: string, password: string) =>
    apiClient.post(`${API_V1_URL}/auth/login`, { email, password }),
  
  logout: () => apiClient.post(`${API_V1_URL}/auth/logout`),
  
  me: () => apiClient.get(`${API_V1_URL}/auth/me`),
};

export const taxProfileAPI = {
  create: (data: any) => apiClient.post(`${API_V1_URL}/tax-profiles/`, data),
  
  get: (id: string) => apiClient.get(`${API_V1_URL}/tax-profiles/${id}`),
  
  update: (id: string, data: any) => apiClient.put(`${API_V1_URL}/tax-profiles/${id}`, sanitizeProfilePayload(data)),
  
  getCurrentUser: () => apiClient.get(`${API_V1_URL}/tax-profiles/current`),
  
  uploadDocument: (profileId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`${API_V1_URL}/tax-profiles/${profileId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const documentsAPI = {
  upload: (file: File, assessmentYear?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (assessmentYear) formData.append('assessment_year', assessmentYear);
    return apiClient.post(`${API_V1_URL}/documents/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
  },

  process: (documentId: string) => apiClient.post(`${API_V1_URL}/documents/${documentId}/process`),

  list: () => apiClient.get(`${API_V1_URL}/documents/`),

  register: (documentType: string, originalFilename: string, assessmentYear?: string) =>
    apiClient.post(`${API_V1_URL}/documents/`, {
      document_type: documentType,
      original_filename: originalFilename,
      assessment_year: assessmentYear,
    }),

  delete: (documentId: string) => apiClient.delete(`${API_V1_URL}/documents/${documentId}`),
};

export const onboardingAPI = {
  start: () => apiClient.post(`${API_V1_URL}/onboarding/session`),
  getSession: () => apiClient.get(`${API_V1_URL}/onboarding/session`),
  sendMessage: (message: string) => apiClient.post(`${API_V1_URL}/onboarding/message`, { message }),
  confirm: (action: 'confirm' | 'reject') => apiClient.post(`${API_V1_URL}/onboarding/confirm`, { action }),
  progress: () => apiClient.get(`${API_V1_URL}/onboarding/progress`),
  documentCandidate: (candidateValues: Record<string, unknown>) => apiClient.post(`${API_V1_URL}/onboarding/document-candidate`, { candidate_values: candidateValues }),
};

export const chatAPI = {
  send: (message: string) => apiClient.post(`${API_V1_URL}/chat`, { message }, { timeout: 20000 }),
};

export const taxAPI = {
  calculate: (payload: any) => apiClient.post(`${API_URL}/api/tax/calculate`, { ...payload, profile: sanitizeProfilePayload(payload.profile) }),
  compareRegimes: (payload: any, allowExpandedIncome = false) => apiClient.post(`${API_URL}/api/tax/compare-regimes`, sanitizeProfilePayload(payload), { params: { allow_expanded_income: allowExpandedIncome } }),
};

export const whatIfAPI = {
  simulate: (changes: Array<{ field: string; operation: string; value: unknown; index?: number }>, baseProfileId?: string) =>
    apiClient.post(`${API_V1_URL}/what-if/simulate`, { base_profile_id: baseProfileId, changes }),
  apply: (changes: Array<{ field: string; operation: string; value: unknown; index?: number }>, baseProfileId: string) =>
    apiClient.post(`${API_V1_URL}/what-if/apply`, { base_profile_id: baseProfileId, changes, confirm: true }),
};

export const deductionsAPI = {
  discover: (regime: 'old' | 'new' = 'old') => apiClient.get(`${API_V1_URL}/deductions/discovery`, { params: { regime } }),
  summary: (regime: 'old' | 'new' = 'old') => apiClient.get(`${API_V1_URL}/deductions/summary`, { params: { regime } }),
};

export const itrAPI = {
  eligibility: () => apiClient.post(`${API_URL}/api/itr/eligibility`),
  selection: () => apiClient.get(`${API_URL}/api/itr/selection`),
  current: () => apiClient.get(`${API_URL}/api/itr/current`),
  prepare: (regime: 'old' | 'new' = 'new', itr_form?: 'ITR-1' | 'ITR-2' | 'ITR-3' | 'ITR-4') => apiClient.post(`${API_URL}/api/itr/prepare`, { regime, itr_form }),
  recalculate: (regime: 'old' | 'new' = 'new', itr_form?: 'ITR-1' | 'ITR-2' | 'ITR-3' | 'ITR-4') => apiClient.post(`${API_URL}/api/itr/recalculate`, { regime, itr_form }),
  ask: (question: string) => apiClient.post(`${API_URL}/api/itr/ask`, { question }),
  pdf: (regime: 'old' | 'new' = 'new', itr_form?: 'ITR-1' | 'ITR-2' | 'ITR-3' | 'ITR-4') => apiClient.post(`${API_URL}/api/itr/pdf`, { regime, itr_form }, { responseType: 'blob' }),
};

export default apiClient;
