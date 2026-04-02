from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" ADD COLUMN IF NOT EXISTS "profile_image" VARCHAR(1024);
        ALTER TABLE "osm_profiles" ADD COLUMN IF NOT EXISTS "profile_image" VARCHAR(1024);
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "profile_image" VARCHAR(1024);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" DROP COLUMN IF EXISTS "profile_image";
        ALTER TABLE "osm_profiles" DROP COLUMN IF EXISTS "profile_image";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "profile_image";
    """
