from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "THAI_PHC_V2"
    POSTGRES_DATABASE_URL: str 
    API_V1_PREFIX: str = "/api/v1"

     # OAuth2 Configuration
    JWT_FIRST_LOGIN_TOKEN_SECRET_KEY: str
    JWT_FIRST_LOGIN_TOKEN_EXPIRE_MINUTES: int = 5
    JWT_FIRST_LOGIN_TOKEN_ALGORITHM: str = "HS256"
    OAUTH2_AUTHORIZATION_CODE_EXPIRE_MINUTES: int = 10  # Development: 10 min, Production: ควรเป็น 5 นาที
    JWT_SESSION_TOKEN_EXPIRE_MINUTES: int = 10
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "RS256"  
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    # Prefer DAYS for refresh token lifetime; if DAYS > 0 it will be used, else fallback to MINUTES
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 60
    # OIDC standard values
    # If not provided via env, issuer can be constructed as {BASE_URL}{API_V1_PREFIX}/auth by the router at runtime
    OIDC_ISSUER: str | None = None
    # Audience identifier for access tokens (Resource Server identifier)
    ACCESS_TOKEN_AUDIENCE: str | None = None

    # Comma-separated list of origins allowed by CORS middleware
    CORS_ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://127.0.0.1:3000,"
        "https://api-thaiphc.hss.moph.go.th,"
        "https://thaiphc.hss.moph.go.th,"
        "https://dashboard.hss.moph.go.th,"
        "https://phc-learning.hss.moph.go.th,"
        "https://osm-workreport.hss.moph.go.th,"
        "https://genh.hss.moph.go.th,"
        "https://phc-management.hss.moph.go.th"
    )
    
    # RSA Keys for JWT signing/verification (backward compatible single-key settings)
    JWT_PRIVATE_KEY_PATH: str = "private_key.pem"
    JWT_PUBLIC_KEY_PATH: str = "public_key.pem"
    JWT_PRIVATE_KEY_INLINE: str | None = None
    JWT_PUBLIC_KEY_INLINE: str | None = None
    # Multi-key rotation support
    # JSON string mapping kid -> private key path, e.g. '{"key-1": "private_key.pem", "key-2": "private_next.pem"}'
    JWT_PRIVATE_KEYS: str | None = None
    # JSON string mapping kid -> public key path, e.g. '{"key-1": "public_key.pem", "key-2": "public_next.pem"}'
    JWT_PUBLIC_KEYS: str | None = None
    # Active KID for signing
    JWT_ACTIVE_KID: str = "key-1"

    # Optional JSON mapping that overrides per-client allowed user types
    OAUTH_CLIENT_ACCESS_RULES: str | None = None

    # Clock skew leeway for JWT verification (seconds)
    JWT_CLOCK_SKEW_SECONDS: int = 30

    # Cookie hardening (production)
    COOKIE_SECURE: bool = True
    # One of: "Lax", "Strict", or "None" (case-sensitive as per RFC6265)
    COOKIE_SAMESITE: str = "Lax"

    # Deprecated: officer permissions are now resolved dynamically from OfficerProfile records.
    SUPER_ADMIN_USER_IDS: str = ""

    # ThaiD integration
    THAID_CLIENT_ID: str | None = None
    THAID_CLIENT_SECRET: str | None = None
    THAID_REQUEST_URI: str | None = None
    THAID_REDIRECT_URI: str | None = None
    # DOPA authorize endpoint (the page users are redirected to for login)
    THAID_AUTHORIZE_URI: str | None = None
    THAID_API_KEY: str = "thaid_integration_key_2025@mof"
    FRONTEND_API_KEY: str | None = None

    # JWT shared configuration for ThaiD tokens
    ALGORITHM: str | None = None
    JWT_EXPIRATION_DELTA_MIN: int = 15
    JWT_REFRESH_TOKEN_EXPIRATION_DELTA_DAYS: int = 7

    # Gen H self-registration (public endpoint — no token required)
    # Set to False after migration period to require officer token for new Gen H accounts
    GEN_H_SELF_REGISTER_ENABLED: bool = True

    # Environment metadata
    ENVIRONMENT: str = "production"

    # Public base URL for building full image URLs (e.g. https://api-thaiphc.hss.moph.go.th)
    PUBLIC_BASE_URL: str | None = None

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",  # allow unknown env vars (e.g., DB_POOL_MIN/MAX)
    }


settings = Settings()