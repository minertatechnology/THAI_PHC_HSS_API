from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauth_clients" ADD COLUMN "allowed_user_types" JSONB;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauth_clients" DROP COLUMN IF EXISTS "allowed_user_types";
    """
