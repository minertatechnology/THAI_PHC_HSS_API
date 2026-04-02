/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_BASE_URL?: string;
    readonly VITE_OAUTH_CLIENT_ID?: string;
    readonly VITE_DEFAULT_SCOPES?: string;
    readonly VITE_OAUTH_CLIENT_SECRET?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}