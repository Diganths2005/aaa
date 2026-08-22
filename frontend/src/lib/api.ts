import axios, { AxiosInstance } from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    apiClient.post('/auth/signup', { email, first_name: firstName, last_name: lastName, password }),
  
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
  
  logout: () => apiClient.post('/auth/logout'),
  
  me: () => apiClient.get('/auth/me'),
};

export const taxProfileAPI = {
  create: (data: any) => apiClient.post('/tax-profiles', data),
  
  get: (id: string) => apiClient.get(`/tax-profiles/${id}`),
  
  update: (id: string, data: any) => apiClient.put(`/tax-profiles/${id}`, data),
  
  getCurrentUser: () => apiClient.get('/tax-profiles/current'),
  
  uploadDocument: (profileId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/tax-profiles/${profileId}/documents`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export default apiClient;
