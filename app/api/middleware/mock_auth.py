from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.middleware.middleware import get_current_user
from app.services.mock_auth_service import MockAuthService


mock_security = HTTPBearer(auto_error=False)


async def get_mock_current_user(credentials: HTTPAuthorizationCredentials = Depends(mock_security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        return MockAuthService.decode_access_token(token)
    except HTTPException as exc:
        # Fall back to the full OAuth middleware for real tokens
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    # Let the core middleware validate and normalize payload
    oauth_user = await get_current_user(credentials)
    return {
        "user": {
            "id": oauth_user.get("user_id"),
            "username": oauth_user.get("citizen_id"),
        },
        "scopes": oauth_user.get("scopes", []),
    }
