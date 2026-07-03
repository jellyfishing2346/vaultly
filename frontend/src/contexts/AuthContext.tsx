'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, User, Account } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  account: Account | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, handle: string, full_name: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('token');
    if (token) {
      api.setToken(token);
      refreshUserData();
    } else {
      setIsLoading(false);
    }
  }, []);

  const refreshUserData = async () => {
    try {
      const data = await api.getMe();
      setUser(data.user);
      setAccount(data.account);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      // Clear invalid token
      localStorage.removeItem('token');
      api.clearToken();
      setUser(null);
      setAccount(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await api.login(email, password);
    const token = response.access_token;
    
    localStorage.setItem('token', token);
    api.setToken(token);
    
    await refreshUserData();
  };

  const signup = async (email: string, handle: string, full_name: string, password: string) => {
    const response = await api.signup(email, handle, full_name, password);
    const token = response.access_token;
    
    localStorage.setItem('token', token);
    api.setToken(token);
    
    await refreshUserData();
  };

  const logout = () => {
    localStorage.removeItem('token');
    api.clearToken();
    setUser(null);
    setAccount(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        account,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
        refreshUserData,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
