from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_notifications" ADD COLUMN IF NOT EXISTS "citizen_id" VARCHAR(13);
        CREATE INDEX IF NOT EXISTS "idx_osm_notific_citizen_id" ON "osm_notifications" ("citizen_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_osm_notific_citizen_id";
        ALTER TABLE "osm_notifications" DROP COLUMN IF EXISTS "citizen_id";"""
