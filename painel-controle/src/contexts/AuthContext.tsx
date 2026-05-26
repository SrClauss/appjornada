import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import api from '@/lib/api';
import type { CurrentUser, LoginResponse } from '@/lib/types';

interface AuthContextValue {
  user: CurrentUser | null;
  token: string | null;
  isLoading: boolean;
  setupNeeded: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  markSetupDone: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [isLoading, setIsLoading] = useState(true);
  const [setupNeeded, setSetupNeeded] = useState(false);

  // Ao montar, verifica setup e token salvo
  useEffect(() => {
    const init = async () => {
      try {
        const { data } = await api.get<{ setup_needed: boolean }>('/auth/setup-needed');
        if (data.setup_needed) {
          setSetupNeeded(true);
          setIsLoading(false);
          return;
        }
      } catch {
        // backend indisponível — continua para tela de login
      }

      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const res = await api.get<CurrentUser>('/auth/me');
        setUser(res.data);
      } catch {
        localStorage.removeItem('token');
        setToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (email: string, password: string) => {
    // Backend espera form-urlencoded (OAuth2PasswordRequestForm)
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const { data } = await api.post<LoginResponse>('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    localStorage.setItem('token', data.access_token);
    setToken(data.access_token);

    const me = await api.get<CurrentUser>('/auth/me', {
      headers: { Authorization: `Bearer ${data.access_token}` },
    });
    setUser(me.data);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const markSetupDone = () => setSetupNeeded(false);

  return (
    <AuthContext.Provider value={{ user, token, isLoading, setupNeeded, login, logout, markSetupDone }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de <AuthProvider>');
  return ctx;
}
