import { apiClient, ApiRequestConfigInit } from "./client";
import { LoginResponse, UserProfile, ChangePasswordPayload, ChangePasswordResult } from "../types/auth";

const AUTH_BASE = "/auth";

interface LoginPayload {
    username: string;
    password: string;
    client_id: string;
    user_type: string;
    scope: string[];
}

export async function loginWithPassword(username: string, password: string): Promise<LoginResponse> {
    const clientId = import.meta.env.VITE_OAUTH_CLIENT_ID;
    if (!clientId) {
        throw new Error("Missing VITE_OAUTH_CLIENT_ID environment variable");
    }

    const scopesRaw = import.meta.env.VITE_DEFAULT_SCOPES ?? "openid profile";
    const scopes = scopesRaw.split(/[,\s]+/).filter(Boolean);

    const payload: LoginPayload = {
        username,
        password,
        client_id: clientId,
        user_type: "officer",
        scope: scopes
    };

    const { data } = await apiClient.post<LoginResponse>(`${AUTH_BASE}/login/json`, payload);
    return data;
}

export async function fetchUserProfile(): Promise<UserProfile> {
    const { data } = await apiClient.get<{ success: boolean; data: UserProfile }>(`${AUTH_BASE}/me`);
    return data.data;
}

export async function requestTokenRefresh(payload: { client_id: string; refresh_token: string; client_secret?: string }): Promise<LoginResponse> {
    const config: ApiRequestConfigInit = {
        skipAuthRefresh: true
    };
    const { data } = await apiClient.post<LoginResponse>(`${AUTH_BASE}/token/refresh`, payload, config);
    return data;
}

export async function revokeRefreshToken(
    clientId: string,
    refreshToken: string,
    clientSecret?: string
): Promise<void> {
    const params = new URLSearchParams();
    params.append("token", refreshToken);
    params.append("token_type_hint", "refresh_token");

    const config: ApiRequestConfigInit = {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        auth: { username: clientId, password: clientSecret ?? "" },
        skipAuthRefresh: true
    };
    await apiClient.post(`${AUTH_BASE}/revoke`, params, config).catch(() => undefined);
}

export async function logoutFromServer(): Promise<void> {
    const config: ApiRequestConfigInit = { skipAuthRefresh: true };
    await apiClient.post(`${AUTH_BASE}/logout`, undefined, config).catch(() => undefined);
}

export async function changePassword(payload: ChangePasswordPayload): Promise<ChangePasswordResult> {
    const { data } = await apiClient.post<ChangePasswordResult>(`${AUTH_BASE}/change-password`, payload);
    return data;
}