from typing import Any, List
from app.services.oauth2_service import Oauth2Service
from fastapi import Request
from app.api.v1.schemas.oauth2_schema import (
    CreateClientSchema,
    UpdateClientSchema,
    DirectLoginRequest,
    RefreshRequest,
    CreateClientBlockRequest,
    ClientBlockQueryParams,
    CreateClientAllowRequest,
    ClientAllowQueryParams,
    ChangePasswordRequest,
)

class Oauth2Controller:
    async def pre_login(citizen_id: str, user_type: str | None = None):
        result = await Oauth2Service.pre_login(citizen_id, user_type)
        return result
    
    async def set_password(citizen_id: str, user_type: str, password: str):
        result = await Oauth2Service.set_password(citizen_id, password, user_type)
        return result
    
    async def login(username: str, password: str, client_id: str, state: str, user_type: str | None, redirect_to: str = "/"):
        result = await Oauth2Service.login(username, password,redirect_to, client_id, state, user_type)
        return result

    async def authorize(request: Request):
        result = await Oauth2Service.authorize(request)
        return result   
    
    async def consent(request: Request, client_id: str, redirect_uri: str, scopes: List[str], state: str):
        result = await Oauth2Service.consent(request, client_id, redirect_uri, scopes, state)
        return result
    
    async def token(request: Request, client_id: str, client_secret: str, grant_type: str, code: str = None, redirect_uri: str = None, refresh_token: str = None, code_verifier: str | None = None):
        result = await Oauth2Service.token(request, client_id, client_secret, grant_type, code, redirect_uri, refresh_token, code_verifier)
        return result

    async def revoke_token(request: Request, client_id: str, client_secret: str, token: str, token_type_hint: str = None):
        result = await Oauth2Service.revoke_token(request, client_id, client_secret, token, token_type_hint)
        return result

    async def create_client(client: CreateClientSchema, request: Request):
        result = await Oauth2Service.create_client(client, request)
        return result
    
    @staticmethod
    async def update_client(client_id: str, payload: UpdateClientSchema, actor: dict):
        return await Oauth2Service.update_client_details(client_id, payload, actor)

    @staticmethod
    async def direct_login(payload: DirectLoginRequest):
        return await Oauth2Service.direct_login(payload)

    @staticmethod
    async def refresh_token_api(payload: RefreshRequest):
        return await Oauth2Service.refresh_token_api(payload)

    @staticmethod
    async def logout(user_id: str, client_id: str, user_type: str | None):
        return await Oauth2Service.logout(user_id, client_id, user_type)
    
    @staticmethod
    async def list_clients():
        return await Oauth2Service.list_oauth_clients()

    @staticmethod
    async def update_client_user_types(client_id: str, user_types: list[str] | None):
        return await Oauth2Service.update_client_user_types(client_id, user_types)

    @staticmethod
    async def get_client_user_types_default(client_id: str):
        return await Oauth2Service.get_client_user_types_default(client_id)

    @staticmethod
    async def set_client_user_types_default(client_id: str, user_types: list[str] | None, actor: dict | None = None):
        return await Oauth2Service.set_client_user_types_default(client_id, user_types, actor)

    @staticmethod
    async def reset_client_user_types_to_default(client_id: str, actor: dict | None = None):
        return await Oauth2Service.reset_client_user_types_to_default(client_id, actor)

    @staticmethod
    async def list_client_blocks(client_id: str, filters: ClientBlockQueryParams | None = None):
        return await Oauth2Service.list_client_blocks(client_id, filters)

    @staticmethod
    async def create_client_block(client_id: str, payload: CreateClientBlockRequest, current_user: dict):
        return await Oauth2Service.create_client_block(client_id, payload, current_user)

    @staticmethod
    async def delete_client_block(client_id: str, block_id: str):
        await Oauth2Service.delete_client_block(client_id, block_id)
        return {"status": "success"}

    @staticmethod
    async def search_block_candidates(user_type: str, query: str, limit: int = 20, offset: int = 0):
        return await Oauth2Service.search_block_candidates(user_type, query, limit, offset)

    @staticmethod
    async def update_client_allowlist_mode(client_id: str, enabled: bool, current_user: dict):
        return await Oauth2Service.update_client_allowlist_mode(client_id, enabled, current_user)

    @staticmethod
    async def list_client_allows(client_id: str, filters: ClientAllowQueryParams | None = None):
        return await Oauth2Service.list_client_allows(client_id, filters)

    @staticmethod
    async def create_client_allow(client_id: str, payload: CreateClientAllowRequest, current_user: dict):
        return await Oauth2Service.create_client_allow(client_id, payload, current_user)

    @staticmethod
    async def delete_client_allow(client_id: str, allow_id: str):
        await Oauth2Service.delete_client_allow(client_id, allow_id)
        return {"status": "success"}

    @staticmethod
    async def change_password(payload: ChangePasswordRequest, current_user: dict):
        return await Oauth2Service.change_password(current_user, payload)

