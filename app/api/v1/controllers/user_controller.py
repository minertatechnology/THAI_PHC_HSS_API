from app.services.user_service import UserService

class UserController:
    async def get_user_info(user_id: str, scopes: list = None, user_type: str = None):
        user_info = await UserService.get_user_info(user_id, scopes, user_type)
        return user_info

