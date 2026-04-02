import React, {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate } from "react-router-dom";
import { AuthState, UserProfile } from "../types/auth";
import {
  loginWithPassword,
  fetchUserProfile,
  logoutFromServer,
  requestTokenRefresh,
  revokeRefreshToken,
} from "../api/auth";
import { storage } from "../utils/storage";
import { apiClient, ApiRequestConfig, setAuthToken } from "../api/client";

interface AuthContextValue extends AuthState {
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  loginWithTokens: (accessToken: string, refreshToken: string | null, expiresIn: number) => Promise<void>;
  logout: () => Promise<void>;
  clearSession: () => void;
  refreshProfile: () => Promise<UserProfile | null>;
  completePasswordChange: () => void;
}

const initialState: AuthState = {
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  user: null,
  expiresAt: null,
  mustChangePassword: false,
};

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);

type AuthProviderProps = {
  children: React.ReactNode;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({
  children,
}: AuthProviderProps) => {
  const [state, setState] = useState<AuthState>(initialState);
  const [isLoading, setLoading] = useState(true);
  const navigate = useNavigate();
  const refreshInFlightRef = useRef<Promise<void> | null>(null);

  const clientId = import.meta.env.VITE_OAUTH_CLIENT_ID;
  const clientSecret = import.meta.env.VITE_OAUTH_CLIENT_SECRET as
    | string
    | undefined;
  const REFRESH_THRESHOLD_MS = 60_000;

  const clearSession = useCallback(() => {
    storage.clear();
    setAuthToken(null);
    setState(initialState);
  }, []);

  const redirectToLogin = useCallback(() => {
    navigate("/login", { replace: true });
  }, [navigate]);

  const forceLogout = useCallback(() => {
    clearSession();
    redirectToLogin();
  }, [clearSession, redirectToLogin]);

  const completePasswordChange = useCallback(() => {
    storage.saveMustChangePassword(false);
    setState((prev) => ({ ...prev, mustChangePassword: false }));
  }, []);

  const bootstrap = useCallback(async () => {
    const storedToken = storage.loadAccessToken();
    if (!storedToken) {
      setLoading(false);
      return;
    }
    setAuthToken(storedToken);
    try {
      const user = await fetchUserProfile();
      const refreshToken = storage.loadRefreshToken();
      const expiresAt = storage.loadExpiresAt();
      const mustChangePassword =
        storage.loadMustChangePassword() || Boolean(user?.is_first_login);
      storage.saveMustChangePassword(mustChangePassword);
      setState({
        isAuthenticated: true,
        accessToken: storedToken,
        refreshToken,
        user,
        expiresAt,
        mustChangePassword,
      });
    } catch (error) {
      clearSession();
    } finally {
      setLoading(false);
    }
  }, [clearSession]);

  const hasBootstrappedRef = useRef(false);
  useEffect(() => {
    if (hasBootstrappedRef.current) {
      return;
    }
    hasBootstrappedRef.current = true;
    bootstrap();
  }, [bootstrap]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await loginWithPassword(username, password);
    const expiresAt = Date.now() + result.expires_in * 1000;

    storage.saveTokens(
      result.access_token,
      result.refresh_token ?? null,
      expiresAt,
    );
    setAuthToken(result.access_token);

    const user = await fetchUserProfile();
    const mustChangePassword =
      Boolean(result.needs_password_change) || Boolean(user?.is_first_login);
    storage.saveMustChangePassword(mustChangePassword);
    setState({
      isAuthenticated: true,
      accessToken: result.access_token,
      refreshToken: result.refresh_token ?? null,
      user,
      expiresAt,
      mustChangePassword,
    });
  }, []);

  /** Accept pre-issued tokens (e.g. from ThaiD callback) and bootstrap a session. */
  const loginWithTokens = useCallback(
    async (accessToken: string, refreshToken: string | null, expiresIn: number) => {
      const expiresAt = Date.now() + expiresIn * 1000;
      storage.saveTokens(accessToken, refreshToken, expiresAt);
      setAuthToken(accessToken);

      const user = await fetchUserProfile();
      const mustChangePassword = Boolean(user?.is_first_login);
      storage.saveMustChangePassword(mustChangePassword);
      setState({
        isAuthenticated: true,
        accessToken,
        refreshToken,
        user,
        expiresAt,
        mustChangePassword,
      });
    },
    [],
  );

  const logout = useCallback(async () => {
    const refreshToken = storage.loadRefreshToken();
    try {
      if (clientId && refreshToken) {
        await revokeRefreshToken(clientId, refreshToken, clientSecret);
      }
      await logoutFromServer();
    } catch (error) {
      // ignore; ensure local session clears regardless of network state
    } finally {
      clearSession();
      redirectToLogin();
    }
  }, [clearSession, clientId, clientSecret, redirectToLogin]);

  const refreshProfile = useCallback(async () => {
    if (!state.accessToken) {
      return null;
    }
    try {
      const profile = await fetchUserProfile();
      const mustChangePassword =
        storage.loadMustChangePassword() || Boolean(profile?.is_first_login);
      storage.saveMustChangePassword(mustChangePassword);
      setState((prev: AuthState) => ({
        ...prev,
        user: profile,
        mustChangePassword,
      }));
      return profile;
    } catch (error) {
      return null;
    }
  }, [state.accessToken]);

  const applyTokenUpdate = useCallback(
    (response: {
      access_token: string;
      refresh_token?: string;
      expires_in: number;
    }) => {
      const nextRefreshToken =
        response.refresh_token ?? storage.loadRefreshToken();
      const expiresAt = Date.now() + response.expires_in * 1000;
      storage.saveTokens(
        response.access_token,
        nextRefreshToken ?? null,
        expiresAt,
      );
      setAuthToken(response.access_token);
      setState((prev) => ({
        ...prev,
        isAuthenticated: true,
        accessToken: response.access_token,
        refreshToken: nextRefreshToken ?? prev.refreshToken,
        expiresAt,
      }));
    },
    [],
  );

  const refreshAccessToken = useCallback(async () => {
    if (!clientId) {
      throw new Error("Missing OAuth client id for refresh");
    }
    if (refreshInFlightRef.current) {
      return refreshInFlightRef.current;
    }
    const inFlight = (async () => {
      const refreshToken = storage.loadRefreshToken();
      if (!refreshToken) {
        throw new Error("Missing refresh token");
      }
      const response = await requestTokenRefresh({
        client_id: clientId,
        refresh_token: refreshToken,
        client_secret: clientSecret,
      });
      applyTokenUpdate(response);
    })()
      .catch((error) => {
        forceLogout();
        throw error;
      })
      .finally(() => {
        refreshInFlightRef.current = null;
      });

    refreshInFlightRef.current = inFlight;
    return inFlight;
  }, [applyTokenUpdate, clientId, clientSecret, forceLogout]);

  useEffect(() => {
    if (!state.isAuthenticated || !state.refreshToken || !state.expiresAt) {
      return;
    }
    const interval = window.setInterval(
      () => {
        const remaining = state.expiresAt! - Date.now();
        if (remaining <= REFRESH_THRESHOLD_MS) {
          refreshAccessToken().catch(() => {
            /* handled in refreshAccessToken */
          });
        }
      },
      Math.min(Math.max(REFRESH_THRESHOLD_MS / 2, 15000), REFRESH_THRESHOLD_MS),
    );

    return () => {
      window.clearInterval(interval);
    };
  }, [
    state.isAuthenticated,
    state.refreshToken,
    state.expiresAt,
    refreshAccessToken,
  ]);

  useEffect(() => {
    const requestInterceptor = apiClient.interceptors.request.use(
      async (config: ApiRequestConfig) => {
        if (config.skipAuthRefresh) {
          return config;
        }
        if (!state.isAuthenticated || !state.refreshToken || !state.expiresAt) {
          return config;
        }
        const remaining = state.expiresAt - Date.now();
        if (remaining <= REFRESH_THRESHOLD_MS) {
          await refreshAccessToken();
          const latestToken = storage.loadAccessToken();
          if (latestToken) {
            const headers = (config.headers ?? {}) as any;
            headers.Authorization = `Bearer ${latestToken}`;
            config.headers = headers;
          }
        }
        return config;
      },
    );

    const responseInterceptor = apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const status = error?.response?.status;
        const originalRequest = error?.config as ApiRequestConfig | undefined;

        if (
          status === 401 &&
          originalRequest &&
          !originalRequest.skipAuthRefresh &&
          !originalRequest._retry
        ) {
          originalRequest._retry = true;
          if (state.refreshToken) {
            try {
              await refreshAccessToken();
              const latestToken = storage.loadAccessToken();
              if (latestToken) {
                const headers = (originalRequest.headers ?? {}) as any;
                headers.Authorization = `Bearer ${latestToken}`;
                originalRequest.headers = headers;
              }
              return apiClient(originalRequest);
            } catch (refreshError) {
              forceLogout();
              return Promise.reject(refreshError);
            }
          } else {
            forceLogout();
          }
        } else if (status === 401) {
          forceLogout();
        }

        return Promise.reject(error);
      },
    );

    return () => {
      apiClient.interceptors.request.eject(requestInterceptor);
      apiClient.interceptors.response.eject(responseInterceptor);
    };
  }, [
    forceLogout,
    refreshAccessToken,
    state.expiresAt,
    state.isAuthenticated,
    state.refreshToken,
  ]);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      isLoading,
      login,
      loginWithTokens,
      logout,
      clearSession,
      refreshProfile,
      completePasswordChange,
    }),
    [state, isLoading, login, loginWithTokens, logout, clearSession, refreshProfile, completePasswordChange],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuthContext(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within an AuthProvider");
  }
  return ctx;
}
