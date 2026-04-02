from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "news_articles" ADD COLUMN "platforms" JSONB NOT NULL DEFAULT '[]'::jsonb;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "news_articles" DROP COLUMN "platforms";"""
