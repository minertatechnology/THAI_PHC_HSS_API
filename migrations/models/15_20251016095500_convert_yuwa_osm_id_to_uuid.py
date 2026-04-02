from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    ALTER TABLE "yuwa_osm_user" ADD COLUMN "id_uuid" UUID DEFAULT gen_random_uuid();
    UPDATE "yuwa_osm_user" SET "id_uuid" = gen_random_uuid() WHERE "id_uuid" IS NULL;
        ALTER TABLE "yuwa_osm_user" DROP CONSTRAINT IF EXISTS "yuwa_osm_user_pkey";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN "id";
        ALTER TABLE "yuwa_osm_user" RENAME COLUMN "id_uuid" TO "id";
        ALTER TABLE "yuwa_osm_user" ADD PRIMARY KEY ("id");
    DROP SEQUENCE IF EXISTS "yuwa_osm_user_id_seq";
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "yuwa_osm_user" ADD COLUMN "id_int" SERIAL;
        ALTER TABLE "yuwa_osm_user" DROP CONSTRAINT IF EXISTS "yuwa_osm_user_pkey";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN "id";
        ALTER TABLE "yuwa_osm_user" RENAME COLUMN "id_int" TO "id";
        ALTER TABLE "yuwa_osm_user" ADD PRIMARY KEY ("id");
    """
