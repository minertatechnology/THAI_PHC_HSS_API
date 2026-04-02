const ACCESS_TOKEN_KEY = "officer_admin_access_token";
const REFRESH_TOKEN_KEY = "officer_admin_refresh_token";
const EXPIRES_AT_KEY = "officer_admin_expires_at";
const PASSWORD_ENFORCE_KEY = "officer_admin_require_password_change";

export const storage = {
    saveTokens(accessToken: string, refreshToken: string | null, expiresAt: number | null) {
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
        if (refreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
        } else {
            localStorage.removeItem(REFRESH_TOKEN_KEY);
        }
        if (expiresAt) {
            localStorage.setItem(EXPIRES_AT_KEY, String(expiresAt));
        } else {
            localStorage.removeItem(EXPIRES_AT_KEY);
        }
    },
    saveMustChangePassword(required: boolean) {
        if (required) {
            localStorage.setItem(PASSWORD_ENFORCE_KEY, "1");
        } else {
            localStorage.removeItem(PASSWORD_ENFORCE_KEY);
        }
    },
    loadAccessToken(): string | null {
        return localStorage.getItem(ACCESS_TOKEN_KEY);
    },
    loadRefreshToken(): string | null {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    },
    loadExpiresAt(): number | null {
        const raw = localStorage.getItem(EXPIRES_AT_KEY);
        return raw ? Number(raw) : null;
    },
    loadMustChangePassword(): boolean {
        return localStorage.getItem(PASSWORD_ENFORCE_KEY) === "1";
    },
    clear() {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(EXPIRES_AT_KEY);
        localStorage.removeItem(PASSWORD_ENFORCE_KEY);
    }
};