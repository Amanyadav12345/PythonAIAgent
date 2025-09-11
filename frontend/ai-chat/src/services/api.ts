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

// Add authentication to requests (except login)
api.interceptors.request.use((config) => {
  // Skip auth for login endpoints
  if (config.url?.includes('/login') || config.url?.includes('/persons/authenticate')) {
    return config;
  }
  
  // Get the stored basic auth token (from login API response)
  const basicAuth = localStorage.getItem('basic_auth');
  
  // Set authorization header similar to SharedPref.token pattern
  config.headers.Authorization = basicAuth || '';
  config.headers['Content-Type'] = 'application/json';
  
  console.log('🔐 Using stored token for API request to:', config.url, {
    hasToken: !!basicAuth,
    tokenPreview: basicAuth ? `${basicAuth.substring(0, 10)}...` : 'No token'
  });
  
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear all auth tokens on 401 error
      localStorage.removeItem('token');
      localStorage.removeItem('basic_auth');
      localStorage.removeItem('user_id');
      localStorage.removeItem('user_info');
      localStorage.removeItem('auth_details');
      localStorage.removeItem('auth_api_response');
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
        // Store the complete API response in localStorage
        localStorage.setItem('auth_api_response', JSON.stringify(authData));
        
        // Store essential auth info for quick access
        localStorage.setItem('token', authData.token);
        localStorage.setItem('user_id', authData.user_record._id);
        localStorage.setItem('basic_auth', basicAuth);
        localStorage.setItem('user_info', JSON.stringify(authData.user_record));
        
        // Store comprehensive auth details for parcel creation and other operations
        const authDetails = {
          // Core user identification
          user_id: authData.user_record._id,
          username: credentials.username,
          auth_field: authData.user_record.auth_field,
          
          // Personal information
          name: authData.user_record.name,
          email: authData.user_record.email,
          phone: authData.user_record.phone,
          
          // Business information
          current_company: authData.user_record.current_company,
          user_type: authData.user_record.user_type,
          individual_user_type: authData.user_record.individual_user_type,
          role_names: authData.user_record.role_names,
          roles: authData.user_record.roles,
          
          // System information
          token: authData.token,
          basic_auth: basicAuth,
          num_id: authData.user_record.num_id,
          preferred_language: authData.user_record.preferred_language,
          
          // Profile settings
          profile_page_settings: authData.user_record.profile_page_settings,
          public_profile_url: authData.user_record.public_profile_url,
          
          // Contact information
          alternate_email_addresses: authData.user_record.alternate_email_addresses,
          alternate_phone_numbers: authData.user_record.alternate_phone_numbers,
          postal_addresses: authData.user_record.postal_addresses,
          
          // App data
          app_ids: authData.user_record.app_ids,
          contact_list: authData.user_record.contact_list,
          
          // Location and operational data
          current_operation_location: authData.user_record.current_operation_location,
          last_vehicle_search_ticket_created_at: authData.user_record.last_vehicle_search_ticket_created_at,
          
          // Media
          photos: authData.user_record.photos,
          
          // System metadata
          _id: authData.user_record._id,
          _created: authData.user_record._created,
          _updated: authData.user_record._updated,
          _version: authData.user_record._version,
          _etag: authData.user_record._etag,
          record_status: authData.user_record.record_status,
          source: authData.user_record.source,
          
          // Complete user record for any additional needs
          user_record: authData.user_record,
          
          // API response metadata
          api_response: {
            ok: authData.ok,
            statusText: authData.statusText,
            data: authData.data
          }
        };
        localStorage.setItem('auth_details', JSON.stringify(authDetails));
        
        console.log('✅ Login successful! Stored auth data:', {
          token: authData.token.substring(0, 10) + '...',
          user_id: authData.user_record._id,
          basic_auth: basicAuth.substring(0, 10) + '...',
          username: authData.user_record.name
        });
        
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
    localStorage.removeItem('auth_details');
    localStorage.removeItem('auth_api_response');
  },
  
  // Method to get complete auth details for API operations
  getAuthDetails: () => {
    const authDetails = localStorage.getItem('auth_details');
    return authDetails ? JSON.parse(authDetails) : null;
  },
  
  // Method to get the complete original API response
  getAuthApiResponse: () => {
    const authApiResponse = localStorage.getItem('auth_api_response');
    return authApiResponse ? JSON.parse(authApiResponse) : null;
  }
};

export const chatAPI = {
  sendMessage: async (message: string): Promise<ChatResponse> => {
    // Get user ID from localStorage
    const user_id = localStorage.getItem('user_id') || '';
    const response = await api.post('/chat', { message, user_id });
    return response.data;
  },
};

export default api;