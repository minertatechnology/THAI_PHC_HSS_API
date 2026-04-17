import axios, { AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";
import { storage } from "../utils/storage";

export type ApiRequestConfig = InternalAxiosRequestConfig & {
    skipAuthRefresh?: boolean;
    _retry?: boolean;
};

export type ApiRequestConfigInit = AxiosRequestConfig & {
    skipAuthRefresh?: boolean;
    _retry?: boolean;
};

const resolveBaseURL = (): string => {
    const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
    if (!configuredBaseUrl) {
        return "/api/v1";
    }
    return configuredBaseUrl;
};

const baseURL = resolveBaseURL();

export const apiClient = axios.create({
    baseURL
});

apiClient.interceptors.request.use((config: ApiRequestConfig) => {
    const token = storage.loadAccessToken();
    if (token) {
        const headers = (config.headers ?? {}) as any;
        headers.Authorization = `Bearer ${token}`;
        config.headers = headers;
    }
    return config;
});

export function setAuthToken(token: string | null) {
    if (!token) {
        delete apiClient.defaults.headers.common.Authorization;
        return;
    }
    apiClient.defaults.headers.common.Authorization = `Bearer ${token}`;
}

export const api = apiClient;