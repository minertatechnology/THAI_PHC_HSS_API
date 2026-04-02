from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauth_clients" ADD "consent_url" TEXT;
        ALTER TABLE "oauth_clients" ADD "login_url" TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauth_clients" DROP COLUMN "consent_url";
        ALTER TABLE "oauth_clients" DROP COLUMN "login_url";"""
