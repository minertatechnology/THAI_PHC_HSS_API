from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_profiles" RENAME COLUMN "userKey" TO "user_key";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_profiles" RENAME COLUMN "user_key" TO "userKey";
    """
