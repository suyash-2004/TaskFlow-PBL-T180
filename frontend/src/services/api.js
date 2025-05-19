import axios from 'axios';

// Get the API base URL from the window or use default
const API_BASE_URL = window.API_BASE_URL || '/api';
console.log('API Service: Using base URL:', API_BASE_URL);

// Create axios instance with proper base URL
const api = axios.create({
  baseURL: '/', // Keep this as '/' since we're using Vite's proxy
  headers: {
    'Content-Type': 'application/json',
  },
  // Add timeout and other configuration
  timeout: 10000, // 10 seconds timeout
});

// Add request interceptor for debugging
api.interceptors.request.use(
  config => {
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, config.params || {});
    return config;
  },
  error => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  response => {
    console.log(`API Response: ${response.status} ${response.config.url}`, response.data);
    return response;
  },
  error => {
    // Log errors for debugging
    console.error('API Error:', error.message);
    if (error.response) {
      console.error('Response data:', error.response.data);
      console.error('Response status:', error.response.status);
    }
    return Promise.reject(error);
  }
);

export default api; 