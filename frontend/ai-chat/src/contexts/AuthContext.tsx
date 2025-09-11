import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, UserRecord } from '../types/api';
import { authAPI } from '../services/api';

interface AuthContextType {
  user: User | null;
  login: (token: string, userRecord?: UserRecord) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const login = async (token: string, userRecord?: UserRecord) => {
    localStorage.setItem('token', token);
    
    try {
      let userData: User;
      
      // If we have userRecord from direct auth API, use it
      if (userRecord) {
        userData = {
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
      } else {
        // Fallback to API call
        userData = await authAPI.getMe();
      }
      
      setUser(userData);
    } catch (error) {
      console.error('Login error:', error);
      localStorage.removeItem('token');
      throw error;
    }
  };

  const logout = () => {
    // Clear all auth-related data
    authAPI.logout();
    setUser(null);
  };

  useEffect(() => {
    const checkAuth = async () => {
      // Check for all auth-related localStorage items
      const basicAuth = localStorage.getItem('basic_auth');
      const token = localStorage.getItem('token');
      const userInfo = localStorage.getItem('user_info');
      const authDetails = localStorage.getItem('auth_details');
      const authApiResponse = localStorage.getItem('auth_api_response');
      
      if (basicAuth && (userInfo || authDetails)) {
        try {
          // If we have basic auth and user info, restore from localStorage
          // Prefer authDetails over userInfo as it has more complete data
          let userRecord;
          if (authDetails) {
            userRecord = JSON.parse(authDetails);
          } else if (userInfo) {
            userRecord = JSON.parse(userInfo);
          } else {
            throw new Error('No user data available');
          }
          
          const userData: User = {
            username: userRecord.username || userRecord.auth_field || userRecord._id,
            email: userRecord.email,
            full_name: userRecord.name,
            user_id: userRecord.user_id || userRecord._id,
            name: userRecord.name,
            phone: userRecord.phone?.number,
            current_company: userRecord.current_company,
            user_type: userRecord.user_type,
            role_names: userRecord.role_names,
            token: userRecord.token
          };
          setUser(userData);
          
          console.log('✅ Restored user from localStorage:', {
            user_id: userData.user_id,
            username: userData.username,
            current_company: userData.current_company,
            name: userData.name
          });
        } catch (error) {
          console.error('Error parsing user info from localStorage:', error);
          // Clear invalid data
          localStorage.removeItem('basic_auth');
          localStorage.removeItem('user_info');
          localStorage.removeItem('auth_details');
          localStorage.removeItem('auth_api_response');
        }
      } else if (token) {
        try {
          // Fallback to API call for Bearer token auth
          const userData = await authAPI.getMe();
          setUser(userData);
        } catch (error) {
          localStorage.removeItem('token');
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const value = {
    user,
    login,
    logout,
    isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};