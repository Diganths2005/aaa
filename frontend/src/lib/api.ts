import axios, { AxiosInstance } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_V1_URL = `${API_URL}/api/v1`;

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
  create: (data: any) => apiClient.post(`${API_V1_URL}/tax-profiles`, data),
  
  get: (id: string) => apiClient.get(`${API_V1_URL}/tax-profiles/${id}`),
  
  update: (id: string, data: any) => apiClient.put(`${API_V1_URL}/tax-profiles/${id}`, data),
  
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
  list: () => apiClient.get(`${API_V1_URL}/documents`),

  register: (documentType: string, originalFilename: string, assessmentYear?: string) =>
    apiClient.post(`${API_V1_URL}/documents`, {
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

export default apiClient;
