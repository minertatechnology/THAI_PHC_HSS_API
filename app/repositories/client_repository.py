from typing import List, Optional
from datetime import datetime, timezone
from tortoise.expressions import Q
from app.models.auth_model import OAuthClient, OAuthConsent, OAuthAuthorizationCode, RefreshToken, OAuthClientBlock, OAuthClientAllow, OAuthClientUserTypeDefault
from app.utils.user_identity import encode_user_id_for_oauth, decode_user_id_from_oauth

class ClientRepository:
    async def find_client_by_id(client_id: str):
        return await OAuthClient.get(id=client_id)
    
    async def find_client_by_client_id(client_id: str):
        return await OAuthClient.filter(client_id=client_id).first()
    
    async def find_client_by_client_secret(client_secret: str):
        return await OAuthClient.get(client_secret=client_secret)
    
    async def find_client_by_client_name(client_name: str):
        return await OAuthClient.get(client_name=client_name)   
    
    async def find_client_by_is_active(is_active: bool):
        return await OAuthClient.get(is_active=is_active)

    async def list_clients():
        return await OAuthClient.all().order_by("client_name")
    
    async def find_client_by_created_by(created_by: str):
        return await OAuthClient.get(created_by=created_by)
    
    async def create_client(
        client_id: str,
        client_secret: str,
        client_name: str,
        client_description: Optional[str],
        redirect_uri: str,
        login_url: str,
        consent_url: str,
        scopes: list,
        grant_types: list,
        created_by: str,
        public_client: bool = True,
    ):
        result = await OAuthClient.create(id=client_id, client_id=client_id, client_secret=client_secret, client_name=client_name, client_description=client_description, redirect_uri=redirect_uri, login_url=login_url, consent_url=consent_url, scopes=scopes, grant_types=grant_types, public_client=public_client, is_active=True, created_by=created_by)
        return result

    async def update_client_details(
        client_id: str,
        *,
        client_name: str,
        client_description: Optional[str],
        redirect_uri: str,
        login_url: str,
        consent_url: str,
        scopes: list[str],
        grant_types: list[str],
        public_client: bool,
        updated_by: Optional[str] = None,
    ) -> Optional[OAuthClient]:
        client = await OAuthClient.filter(client_id=client_id).first()
        if not client:
            return None
        client.client_name = client_name
        client.client_description = client_description
        client.redirect_uri = redirect_uri
        client.login_url = login_url
        client.consent_url = consent_url
        client.scopes = scopes
        client.grant_types = grant_types
        client.public_client = public_client
        if updated_by:
            client.updated_by = updated_by
        await client.save()
        await client.refresh_from_db()
        return client

    async def set_allowed_user_types(client_id: str, allowed_user_types: Optional[list[str]]):
        client = await OAuthClient.filter(client_id=client_id).first()
        if not client:
            return None
        client.allowed_user_types = allowed_user_types
        await client.save()
        return client

    async def set_allowlist_enabled(client_id: str, enabled: bool, updated_by: Optional[str] = None) -> Optional[OAuthClient]:
        client = await OAuthClient.filter(client_id=client_id).first()
        if not client:
            return None
        client.allowlist_enabled = bool(enabled)
        if updated_by:
            client.updated_by = updated_by
        await client.save()
        await client.refresh_from_db()
        return client


class OAuthClientBlockRepository:
    @staticmethod
    async def is_user_blocked(client_db_id: str, user_id: str, user_type: str) -> bool:
        return await OAuthClientBlock.filter(client_id=client_db_id, user_id=user_id, user_type=user_type).exists()

    @staticmethod
    async def find_existing_block(client_db_id: str, user_id: str, user_type: str) -> Optional[OAuthClientBlock]:
        return await OAuthClientBlock.filter(client_id=client_db_id, user_id=user_id, user_type=user_type).first()

    @staticmethod
    async def create_block(
        *,
        client_db_id: str,
        user_id: str,
        user_type: str,
        citizen_id: Optional[str],
        full_name: Optional[str],
        note: Optional[str],
        created_by: str,
    ) -> OAuthClientBlock:
        return await OAuthClientBlock.create(
            client_id=client_db_id,
            user_id=user_id,
            user_type=user_type,
            citizen_id=citizen_id,
            full_name=full_name,
            note=note,
            created_by=created_by,
        )

    @staticmethod
    async def list_blocks(
        client_db_id: str,
        *,
        user_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[OAuthClientBlock]:
        query = OAuthClientBlock.filter(client_id=client_db_id)
        if user_type:
            query = query.filter(user_type=user_type)
        if search:
            term = search.strip()
            if term:
                query = query.filter(Q(full_name__icontains=term) | Q(citizen_id__icontains=term))
        return await query.order_by("-created_at").limit(limit)

    @staticmethod
    async def delete_block(block_id: str, client_db_id: str) -> int:
        return await OAuthClientBlock.filter(id=block_id, client_id=client_db_id).delete()


class OAuthClientAllowRepository:
    @staticmethod
    async def is_user_allowed(client_db_id: str, user_id: str, user_type: str) -> bool:
        return await OAuthClientAllow.filter(client_id=client_db_id, user_id=user_id, user_type=user_type).exists()

    @staticmethod
    async def find_existing_allow(client_db_id: str, user_id: str, user_type: str) -> Optional[OAuthClientAllow]:
        return await OAuthClientAllow.filter(client_id=client_db_id, user_id=user_id, user_type=user_type).first()

    @staticmethod
    async def create_allow(
        *,
        client_db_id: str,
        user_id: str,
        user_type: str,
        citizen_id: Optional[str],
        full_name: Optional[str],
        note: Optional[str],
        created_by: str,
    ) -> OAuthClientAllow:
        return await OAuthClientAllow.create(
            client_id=client_db_id,
            user_id=user_id,
            user_type=user_type,
            citizen_id=citizen_id,
            full_name=full_name,
            note=note,
            created_by=created_by,
        )

    @staticmethod
    async def list_allows(
        client_db_id: str,
        *,
        user_type: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[OAuthClientAllow]:
        query = OAuthClientAllow.filter(client_id=client_db_id)
        if user_type:
            query = query.filter(user_type=user_type)
        if search:
            term = search.strip()
            if term:
                query = query.filter(Q(full_name__icontains=term) | Q(citizen_id__icontains=term))
        return await query.order_by("-created_at").limit(limit)

    @staticmethod
    async def delete_allow(allow_id: str, client_db_id: str) -> int:
        return await OAuthClientAllow.filter(id=allow_id, client_id=client_db_id).delete()


class OAuthClientUserTypeDefaultRepository:
    @staticmethod
    async def get_default(client_db_id: str) -> Optional[OAuthClientUserTypeDefault]:
        return await OAuthClientUserTypeDefault.filter(client_id=client_db_id).first()

    @staticmethod
    async def ensure_default(
        client_db_id: str,
        allowed_user_types: Optional[list[str]],
        actor_id: Optional[str] = None,
    ) -> OAuthClientUserTypeDefault:
        existing = await OAuthClientUserTypeDefaultRepository.get_default(client_db_id)
        if existing:
            return existing
        return await OAuthClientUserTypeDefault.create(
            client_id=client_db_id,
            allowed_user_types=allowed_user_types,
            created_by=actor_id,
            updated_by=actor_id,
        )

    @staticmethod
    async def upsert_default(
        client_db_id: str,
        allowed_user_types: Optional[list[str]],
        actor_id: Optional[str] = None,
    ) -> OAuthClientUserTypeDefault:
        existing = await OAuthClientUserTypeDefaultRepository.get_default(client_db_id)
        if existing:
            existing.allowed_user_types = allowed_user_types
            if actor_id:
                existing.updated_by = actor_id
            await existing.save()
            await existing.refresh_from_db()
            return existing
        return await OAuthClientUserTypeDefault.create(
            client_id=client_db_id,
            allowed_user_types=allowed_user_types,
            created_by=actor_id,
            updated_by=actor_id,
        )
    
class OAuthConsentRepository:
    async def create_consent(user_id: str, client_id: str, scopes: List[str], user_type: Optional[str] = None):
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        # Check if consent already exists
        consent = await OAuthConsent.filter(user_id=stored_user_id, client_id=client_id).first()
        if consent:
            # Update existing consent with new scopes
            consent.scopes = scopes
            await consent.save()
            return consent
        # Create new consent
        return await OAuthConsent.create(user_id=stored_user_id, client_id=client_id, scopes=scopes)
    
    async def has_user_consented(user_id: str, client_id: str, scopes: List[str], user_type: Optional[str] = None) -> bool:
        # หา consent ที่มี scopes ครอบคลุม request scopes
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        consent = await OAuthConsent.filter(user_id=stored_user_id, client_id=client_id).first()
        if not consent:
            return False
        
        # ตรวจสอบว่า stored scopes ครอบคลุม request scopes
        stored_scopes = set(consent.scopes)
        request_scopes = set(scopes)
        
        return request_scopes.issubset(stored_scopes)
    
    async def get_user_consented_scopes(user_id: str, client_id: str, user_type: Optional[str] = None) -> List[str]:
        """
        ดึง scopes ที่ user consent แล้วสำหรับ client นี้
        """
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        consent = await OAuthConsent.filter(user_id=stored_user_id, client_id=client_id).first()
        if not consent:
            return []
        return consent.scopes

    
class OAuthAuthorizationCodeRepository:
    async def create_authorization_code(
        code: str,
        user_id: str,
        user_type: str,
        client_id: str,
        scopes: List[str],
        expires_at: datetime,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    nonce: Optional[str] = None,
    ):
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        return await OAuthAuthorizationCode.create(
            code=code,
            user_id=stored_user_id,
            user_type=user_type,
            client_id=client_id,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
            expires_at=expires_at,
        )
    
    async def find_authorization_code_by_code(code: str):
        auth_code = await OAuthAuthorizationCode.get(code=code)
        if auth_code:
            auth_code.user_id = decode_user_id_from_oauth(auth_code.user_id, auth_code.user_type)
        return auth_code
    
    async def delete_authorization_code(code: str):
        return await OAuthAuthorizationCode.filter(code=code).delete()

class RefreshTokenRepository:
    async def create_refresh_token(token: str, user_id: str, user_type: str, client_id: str, scopes: List[str], expires_at: datetime):
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        return await RefreshToken.create(
            token=token,
            user_id=stored_user_id,
            user_type=user_type,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at
        )
    
    async def find_refresh_token_by_token(token: str):
        refresh = await RefreshToken.filter(token=token, is_revoked=False).first()
        if refresh:
            refresh.user_id = decode_user_id_from_oauth(refresh.user_id, refresh.user_type)
        return refresh
    
    async def revoke_refresh_token(token: str):
        return await RefreshToken.filter(token=token).update(is_revoked=True)
    
    async def revoke_all_user_refresh_tokens(user_id: str, client_id: Optional[str], user_type: Optional[str] = None):
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        query = RefreshToken.filter(user_id=stored_user_id)
        if client_id:
            query = query.filter(client_id=client_id)
        return await query.update(is_revoked=True)

    async def revoke_all_client_refresh_tokens(client_id: str) -> int:
        return await RefreshToken.filter(client_id=client_id).update(is_revoked=True)

    async def revoke_all_client_refresh_tokens_except_user(
        user_id: str,
        client_id: str,
        user_type: Optional[str] = None,
    ) -> int:
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        return await RefreshToken.filter(client_id=client_id).exclude(user_id=stored_user_id).update(is_revoked=True)
    
    async def cleanup_expired_refresh_tokens():
        """ลบ refresh tokens ที่หมดอายุแล้ว"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return await RefreshToken.filter(expires_at__lt=now).delete()

    async def has_active_refresh_token(user_id: str, client_id: str, user_type: Optional[str] = None) -> bool:
        """ตรวจสอบว่ามี refresh token ที่ยังใช้งานได้อยู่หรือไม่"""
        stored_user_id = encode_user_id_for_oauth(user_id, user_type)
        now = datetime.now(timezone.utc)
        return await RefreshToken.filter(
            user_id=stored_user_id,
            client_id=client_id,
            is_revoked=False,
            expires_at__gte=now,
        ).exists()