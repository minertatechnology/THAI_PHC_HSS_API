from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "osm_profiles" ADD COLUMN "osm_status" VARCHAR(10);
    ALTER TABLE "osm_profiles" ADD COLUMN "osm_showbbody" VARCHAR(10);
    CREATE INDEX IF NOT EXISTS "idx_osm_profiles_osm_status" ON "osm_profiles" ("osm_status");
    CREATE INDEX IF NOT EXISTS "idx_osm_profiles_osm_showbbody" ON "osm_profiles" ("osm_showbbody");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP INDEX IF EXISTS "idx_osm_profiles_osm_showbbody";
    DROP INDEX IF EXISTS "idx_osm_profiles_osm_status";
    ALTER TABLE "osm_profiles" DROP COLUMN IF EXISTS "osm_showbbody";
    ALTER TABLE "osm_profiles" DROP COLUMN IF EXISTS "osm_status";
    """
