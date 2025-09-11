/**
 * Authentication utilities for managing tokens in localStorage
 */

export interface AuthTokens {
  basicAuth?: string;
  token?: string;
  userId?: string;
  userInfo?: string;
}

export const authUtils = {
  /**
   * Store authentication tokens in localStorage
   */
  storeTokens: (tokens: AuthTokens): void => {
    if (tokens.basicAuth) {
      localStorage.setItem('basic_auth', tokens.basicAuth);
    }
    if (tokens.token) {
      localStorage.setItem('token', tokens.token);
    }
    if (tokens.userId) {
      localStorage.setItem('user_id', tokens.userId);
    }
    if (tokens.userInfo) {
      localStorage.setItem('user_info', tokens.userInfo);
    }
  },

  /**
   * Get stored authentication tokens
   */
  getTokens: (): AuthTokens => {
    return {
      basicAuth: localStorage.getItem('basic_auth') || undefined,
      token: localStorage.getItem('token') || undefined,
      userId: localStorage.getItem('user_id') || undefined,
      userInfo: localStorage.getItem('user_info') || undefined,
    };
  },

  /**
   * Clear all authentication tokens
   */
  clearTokens: (): void => {
    localStorage.removeItem('basic_auth');
    localStorage.removeItem('token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_info');
  },

  /**
   * Get the best available authorization header (raw token format)
   */
  getAuthHeader: (): string | null => {
    const tokens = authUtils.getTokens();
    
    // Prefer basic auth for direct API calls (use raw token as per SharedPref.token pattern)
    if (tokens.basicAuth) {
      return tokens.basicAuth;
    }
    
    // Fallback to Bearer token
    if (tokens.token) {
      return `Bearer ${tokens.token}`;
    }
    
    return null;
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated: (): boolean => {
    const tokens = authUtils.getTokens();
    return !!(tokens.basicAuth || tokens.token);
  },

  /**
   * Get current user ID
   */
  getCurrentUserId: (): string | null => {
    return localStorage.getItem('user_id');
  },

  /**
   * Debug: Log current auth status
   */
  debugAuthStatus: (): void => {
    const tokens = authUtils.getTokens();
    console.log('🔐 Auth Status:', {
      hasBasicAuth: !!tokens.basicAuth,
      hasToken: !!tokens.token,
      hasUserId: !!tokens.userId,
      hasUserInfo: !!tokens.userInfo,
      basicAuthPreview: tokens.basicAuth ? `${tokens.basicAuth.substring(0, 10)}...` : null,
      tokenPreview: tokens.token ? `${tokens.token.substring(0, 10)}...` : null,
      userId: tokens.userId,
      isAuthenticated: authUtils.isAuthenticated(),
      authHeader: authUtils.getAuthHeader()?.substring(0, 20) + '...' || null
    });
  }
};