from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "yuwa_osm_code" VARCHAR(9);
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "source_people_id" UUID;
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "transferred_by" UUID;
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "transferred_at" TIMESTAMPTZ;

        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "yuwa_osm_code" VARCHAR(9);
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "is_transferred" BOOL NOT NULL DEFAULT FALSE;
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "transferred_at" TIMESTAMPTZ;
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "transferred_by" UUID;
        ALTER TABLE "people_user" ADD COLUMN IF NOT EXISTS "yuwa_osm_id" UUID;

        CREATE INDEX IF NOT EXISTS "idx_people_user_yuwa_osm_code" ON "people_user" ("yuwa_osm_code");
        CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_user_yuwa_osm_code" ON "yuwa_osm_user" ("yuwa_osm_code");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_people_user_yuwa_osm_code";
        DROP INDEX IF EXISTS "idx_yuwa_osm_user_yuwa_osm_code";

        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "yuwa_osm_code";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "source_people_id";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "transferred_by";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "transferred_at";

        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "yuwa_osm_code";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "is_transferred";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "transferred_at";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "transferred_by";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "yuwa_osm_id";
    """
