from datetime import datetime, timedelta, timezone
from pathlib import Path
import base64
import binascii
import logging
from typing import Dict, Tuple, Union
import jwt 
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from app.configs.config import settings


logger = logging.getLogger(__name__)

# Cache RSA keys to avoid reading from disk on every request
_PRIVATE_KEY_CACHE: Union[bytes, str, RSAPrivateKey, None] = None
_PUBLIC_KEY_CACHE: Union[bytes, str, RSAPublicKey, None] = None
_PRIVATE_KEYS_BY_KID: Dict[str, Union[bytes, str, RSAPrivateKey]] | None = None
_PUBLIC_KEYS_BY_KID: Dict[str, Union[bytes, str, RSAPublicKey]] | None = None

def _is_asymmetric_algorithm() -> bool:
    alg = (settings.JWT_ALGORITHM or "").upper()
    return alg.startswith("RS") or alg.startswith("PS") or alg.startswith("ES")


def _normalize_key_material(raw: bytes) -> bytes:
    """Normalize key bytes by trimming and expanding escaped newlines if necessary."""
    stripped = raw.strip()
    if b"\\n" in stripped and b"\n" not in stripped:
        try:
            text = stripped.decode("utf-8")
            stripped = text.replace("\\r", "").replace("\\n", "\n").encode("utf-8")
        except UnicodeDecodeError:
            pass
    return stripped


def _deserialize_private_key(key_bytes: bytes) -> RSAPrivateKey:
    """Attempt to deserialize RSA private key supporting PEM or DER payloads."""
    normalized = _normalize_key_material(key_bytes)
    try:
        return serialization.load_pem_private_key(normalized, password=None)
    except ValueError as pem_exc:
        # If the content still looks like PEM, bubble up immediately
        if normalized.startswith(b"-----BEGIN"):
            raise
        try:
            der_bytes = base64.b64decode(normalized, validate=True)
        except (binascii.Error, ValueError) as decode_exc:
            raise pem_exc from decode_exc
        try:
            return serialization.load_der_private_key(der_bytes, password=None)
        except ValueError as der_exc:
            raise pem_exc from der_exc


def _deserialize_public_key(key_bytes: bytes) -> RSAPublicKey:
    """Attempt to deserialize RSA public key supporting PEM or DER payloads."""
    normalized = _normalize_key_material(key_bytes)
    try:
        return serialization.load_pem_public_key(normalized)
    except ValueError as pem_exc:
        if normalized.startswith(b"-----BEGIN"):
            raise
        try:
            der_bytes = base64.b64decode(normalized, validate=True)
        except (binascii.Error, ValueError) as decode_exc:
            raise pem_exc from decode_exc
        try:
            return serialization.load_der_public_key(der_bytes)
        except ValueError as der_exc:
            raise pem_exc from der_exc


def _load_private_key():
    """โหลด private key สำหรับ sign JWT พร้อม cache ในหน่วยความจำ"""
    global _PRIVATE_KEY_CACHE
    if _PRIVATE_KEY_CACHE is not None:
        return _PRIVATE_KEY_CACHE
    try:
        if settings.JWT_PRIVATE_KEY_INLINE:
            pem_bytes = settings.JWT_PRIVATE_KEY_INLINE.encode()
        else:
            key_path = Path(settings.JWT_PRIVATE_KEY_PATH)
            pem_bytes = key_path.read_bytes()
        if not pem_bytes.strip():
            raise ValueError("Private key file is empty")
        if _is_asymmetric_algorithm():
            _PRIVATE_KEY_CACHE = _deserialize_private_key(pem_bytes)
        else:
            _PRIVATE_KEY_CACHE = pem_bytes
    except FileNotFoundError as exc:
        logger.error("JWT private key not found at %s", settings.JWT_PRIVATE_KEY_PATH)
        if _is_asymmetric_algorithm():
            raise RuntimeError(
                "JWT_PRIVATE_KEY_PATH is missing but JWT_ALGORITHM requires an asymmetric key"
            ) from exc
        _PRIVATE_KEY_CACHE = settings.JWT_SECRET_KEY
    except Exception as exc:
        logger.error("Failed to load JWT private key: %s", exc)
        if _is_asymmetric_algorithm():
            raise
        _PRIVATE_KEY_CACHE = settings.JWT_SECRET_KEY
    return _PRIVATE_KEY_CACHE

def _load_public_key():
    """โหลด public key สำหรับ verify JWT พร้อม cache ในหน่วยความจำ"""
    global _PUBLIC_KEY_CACHE
    if _PUBLIC_KEY_CACHE is not None:
        return _PUBLIC_KEY_CACHE
    try:
        if settings.JWT_PUBLIC_KEY_INLINE:
            pem_bytes = settings.JWT_PUBLIC_KEY_INLINE.encode()
        else:
            key_path = Path(settings.JWT_PUBLIC_KEY_PATH)
            pem_bytes = key_path.read_bytes()
        if not pem_bytes.strip():
            raise ValueError("Public key file is empty")
        if _is_asymmetric_algorithm():
            _PUBLIC_KEY_CACHE = _deserialize_public_key(pem_bytes)
        else:
            _PUBLIC_KEY_CACHE = pem_bytes
    except FileNotFoundError as exc:
        logger.error("JWT public key not found at %s", settings.JWT_PUBLIC_KEY_PATH)
        if _is_asymmetric_algorithm():
            raise RuntimeError(
                "JWT_PUBLIC_KEY_PATH is missing but JWT_ALGORITHM requires an asymmetric key"
            ) from exc
        _PUBLIC_KEY_CACHE = settings.JWT_SECRET_KEY
    except Exception as exc:
        logger.error("Failed to load JWT public key: %s", exc)
        if _is_asymmetric_algorithm():
            raise
        _PUBLIC_KEY_CACHE = settings.JWT_SECRET_KEY
    return _PUBLIC_KEY_CACHE

def _load_private_keys_by_kid() -> Dict[str, Union[bytes, str, RSAPrivateKey]]:
    global _PRIVATE_KEYS_BY_KID
    if _PRIVATE_KEYS_BY_KID is not None:
        return _PRIVATE_KEYS_BY_KID
    mapping: Dict[str, bytes] = {}
    try:
        if settings.JWT_PRIVATE_KEYS:
            paths = json.loads(settings.JWT_PRIVATE_KEYS)
            for kid, path in paths.items():
                with open(path, 'rb') as f:
                    pem_bytes = f.read()
                    if not pem_bytes.strip():
                        raise ValueError(f"Private key file for kid {kid} is empty")
                    if _is_asymmetric_algorithm():
                        mapping[kid] = _deserialize_private_key(pem_bytes)
                    else:
                        mapping[kid] = pem_bytes
    except Exception:
        mapping = {}
    if not mapping:
        # fallback to single key
        mapping = {settings.JWT_ACTIVE_KID: _load_private_key()}
    _PRIVATE_KEYS_BY_KID = mapping
    return mapping

def _load_public_keys_by_kid() -> Dict[str, Union[bytes, str, RSAPublicKey]]:
    global _PUBLIC_KEYS_BY_KID
    if _PUBLIC_KEYS_BY_KID is not None:
        return _PUBLIC_KEYS_BY_KID
    mapping: Dict[str, bytes] = {}
    try:
        if settings.JWT_PUBLIC_KEYS:
            paths = json.loads(settings.JWT_PUBLIC_KEYS)
            for kid, path in paths.items():
                with open(path, 'rb') as f:
                    pem_bytes = f.read()
                    if not pem_bytes.strip():
                        raise ValueError(f"Public key file for kid {kid} is empty")
                    if _is_asymmetric_algorithm():
                        mapping[kid] = _deserialize_public_key(pem_bytes)
                    else:
                        mapping[kid] = pem_bytes
    except Exception:
        mapping = {}
    if not mapping:
        mapping = {settings.JWT_ACTIVE_KID: _load_public_key()}
    _PUBLIC_KEYS_BY_KID = mapping
    return mapping

def get_active_signing_key() -> Tuple[str, bytes]:
    """Return (kid, private_key_bytes) for signing"""
    kid = settings.JWT_ACTIVE_KID
    keys = _load_private_keys_by_kid()
    return kid, keys.get(kid) or _load_private_key()
def create_session_token(user_id: str,user_type: str = None) -> str:
    expire = datetime.now() + timedelta(minutes=settings.JWT_SESSION_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "user_id": user_id,
        "ut": user_type,
        "exp": expire
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
def decode_jwt_session_token(session_token: str):
    return jwt.decode(session_token, settings.JWT_SECRET_KEY, algorithms="HS256", leeway=getattr(settings, "JWT_CLOCK_SKEW_SECONDS", 0))

def decode_jwt_token(token: str):
    """
    ถอดรหัส JWT token จาก header Authorization
    """
    
    try:
        # ใช้ public key สำหรับ verify
        key = _load_public_key()
        # ปิดการ verify audience ที่ชั้นนี้ เพราะเราตรวจ iss/aud ที่ middleware แล้ว
        # ยังคงตรวจลายเซ็นและ exp ตามปกติ
        # Respect small clock skew leeway
        result = jwt.decode(
            token,
            key,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_aud": False},
            leeway=getattr(settings, "JWT_CLOCK_SKEW_SECONDS", 0),
        )
        return result
    except Exception as e:
        raise e

def create_access_token(
    user_id: str,
    client_id: str | None = None,
    user_type: str | None = None,
    scopes: list[str] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    scope_str = " ".join(scopes) if scopes else None
    issuer = settings.OIDC_ISSUER  # may be None; resource server must handle accordingly
    audience = settings.ACCESS_TOKEN_AUDIENCE or client_id
    payload = {
        "sub": user_id,                        # subject: ตัวแทน user id
        "iat": now,                           # issued at
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),  # หมดอายุ
        "type": "access",                     # แท็กประเภท token
        "cid": client_id,                      # client ID (custom)
        "ut": user_type,                       # user type (custom)
    }
    if issuer:
        payload["iss"] = issuer
    if audience:
        payload["aud"] = audience
    if scope_str:
        payload["scope"] = scope_str
    # ใช้ private key สำหรับ sign
    kid, key = get_active_signing_key()
    token = jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM, headers={"kid": kid})
    return token

def create_refresh_token(user_id: str, client_id: str = None,user_type: str = None) -> str:
    now = datetime.now(timezone.utc)
    # Respect DAYS if configured; fallback to MINUTES
    if getattr(settings, "JWT_REFRESH_TOKEN_EXPIRE_DAYS", 0) and settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS > 0:
        exp = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        exp = now + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": exp,
        "type": "refresh",
        "cid": client_id,                      # client ID
        "ut": user_type
    }
    # ใช้ private key สำหรับ sign
    kid, key = get_active_signing_key()
    token = jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM, headers={"kid": kid})
    return token


def create_id_token(user_id: str, client_id: str, issuer: str, auth_time: datetime | None = None, nonce: str | None = None) -> str:
    """
    Create an OpenID Connect ID Token (JWT) with standard claims.
    - iss: issuer URL
    - sub: user id (subject)
    - aud: client_id
    - iat/exp: token timestamps
    - auth_time: optional authentication time
    - nonce: optional nonce echoed back to the client
    """
    now = datetime.now(timezone.utc)
    payload = {
        "iss": issuer,
        "sub": user_id,
        "aud": client_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if auth_time:
        # NumericDate per spec
        payload["auth_time"] = int(auth_time.timestamp())
    if nonce:
        payload["nonce"] = nonce
    kid, key = get_active_signing_key()
    return jwt.encode(payload, key, algorithm=settings.JWT_ALGORITHM, headers={"kid": kid})


def create_first_login_token(citizen_id: str, user_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": citizen_id,
        "ut": user_type,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_FIRST_LOGIN_TOKEN_EXPIRE_MINUTES),
        "purpose": "set-password",
    }
    key = settings.JWT_FIRST_LOGIN_TOKEN_SECRET_KEY
    token = jwt.encode(payload, key, algorithm=settings.JWT_FIRST_LOGIN_TOKEN_ALGORITHM)
    return token


def decode_first_login_token(token: str):
    try:
        key = settings.JWT_FIRST_LOGIN_TOKEN_SECRET_KEY
        result = jwt.decode(token, key, algorithms=[settings.JWT_FIRST_LOGIN_TOKEN_ALGORITHM])
        return result
    except Exception as e:
        print("decode first login token error:", e)
        print("decode first login token error type:", type(e))
        raise e
