import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import useAppStore from '@/store';

const API_BASE_URL = '/api';

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    const { showNotification } = useAppStore.getState();

    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const data = error.response.data as { detail?: string; message?: string };

      switch (status) {
        case 401:
          // Unauthorized - clear token and redirect to login if needed
          localStorage.removeItem('authToken');
          showNotification({
            type: 'error',
            content: 'Authentication failed. Please log in again.',
          });
          break;
        case 403:
          showNotification({
            type: 'error',
            content: 'You do not have permission to perform this action.',
          });
          break;
        case 404:
          showNotification({
            type: 'error',
            content: data?.detail || 'Resource not found.',
          });
          break;
        case 422:
          // Validation error
          showNotification({
            type: 'error',
            content: data?.detail || 'Validation error occurred.',
          });
          break;
        case 500:
          showNotification({
            type: 'error',
            content: 'Server error occurred. Please try again later.',
          });
          break;
        default:
          showNotification({
            type: 'error',
            content: data?.detail || `Error: ${status}`,
          });
      }
    } else if (error.request) {
      // Request made but no response received
      showNotification({
        type: 'error',
        content: 'Network error. Please check your connection.',
      });
    } else {
      // Something else happened
      showNotification({
        type: 'error',
        content: 'An unexpected error occurred.',
      });
    }

    return Promise.reject(error);
  }
);

export default api;
