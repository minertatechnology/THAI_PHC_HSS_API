from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "prefix" VARCHAR(50);
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "line_id" VARCHAR(100);
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "school" VARCHAR(255);
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "organization" VARCHAR(255);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "organization";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "school";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "line_id";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "prefix";
    """
