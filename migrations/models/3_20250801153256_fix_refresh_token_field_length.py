from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "refresh_tokens" ALTER COLUMN "token" TYPE VARCHAR(1000) USING "token"::VARCHAR(1000);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "refresh_tokens" ALTER COLUMN "token" TYPE VARCHAR(255) USING "token"::VARCHAR(255);"""
