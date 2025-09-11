import axios from 'axios';
import { LoginRequest, LoginResponse, User, ChatResponse } from '../types/api';

const API_BASE_URL = 'http://localhost:8000';
const AUTH_API_BASE_URL = 'https://35.244.19.78:8042';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Separate axios instance for direct auth API calls
const authApi = axios.create({
  baseURL: AUTH_API_BASE_URL,
  timeout: 30000,
  // For development - ignore SSL certificate issues
  httpsAgent: false,
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    try {
      // Create Basic Auth header
      const basicAuth = btoa(`${credentials.username}:${credentials.password}`);
      
      // Build the WHERE query as per API specification
      const whereQuery = {
        "$or": [
          {"username": credentials.username},
          {"password": credentials.password}
        ]
      };
      
      // Make the authentication request
      const response = await authApi.get('/persons/authenticate', {
        params: {
          page: 1,
          max_results: 10,
          where: JSON.stringify(whereQuery)
        },
        headers: {
          'Authorization': `Basic ${basicAuth}`,
          'Content-Type': 'application/json'
        }
      });
      
      const authData = response.data;
      
      // Validate response
      if (authData.ok && authData.token && authData.user_record) {
        // Store auth info in localStorage
        localStorage.setItem('token', authData.token);
        localStorage.setItem('user_id', authData.user_record._id);
        localStorage.setItem('basic_auth', basicAuth);
        localStorage.setItem('user_info', JSON.stringify(authData.user_record));
        
        return authData;
      } else {
        throw new Error(authData.statusText || 'Authentication failed');
      }
    } catch (error: any) {
      console.error('Auth API Error:', error);
      
      // If direct API fails, fallback to backend auth
      try {
        const backendResponse = await api.post('/login', credentials);
        return {
          ...backendResponse.data,
          access_token: backendResponse.data.access_token,
          token_type: backendResponse.data.token_type
        };
      } catch (backendError) {
        throw error; // Throw original auth API error
      }
    }
  },
  
  getMe: async (): Promise<User> => {
    // Try to get user from localStorage first
    const userInfo = localStorage.getItem('user_info');
    if (userInfo) {
      const userRecord = JSON.parse(userInfo);
      return {
        username: userRecord.auth_field || userRecord._id,
        email: userRecord.email,
        full_name: userRecord.name,
        user_id: userRecord._id,
        name: userRecord.name,
        phone: userRecord.phone?.number,
        current_company: userRecord.current_company,
        user_type: userRecord.user_type,
        role_names: userRecord.role_names,
        token: userRecord.token
      };
    }
    
    // Fallback to backend API
    const response = await api.get('/users/me');
    return response.data;
  },
  
  // New method to get basic auth header for API calls
  getBasicAuthHeader: (): string | null => {
    return localStorage.getItem('basic_auth');
  },
  
  // Method to clear auth data
  logout: (): void => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('basic_auth');
    localStorage.removeItem('user_info');
  }
};

export const chatAPI = {
  sendMessage: async (message: string): Promise<ChatResponse> => {
    const response = await api.post('/chat', { message, user_id: '' });
    return response.data;
  },
};

export default api;