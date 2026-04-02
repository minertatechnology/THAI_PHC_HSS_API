from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_children" ADD "citizen_id" VARCHAR(13) UNIQUE;
        ALTER TABLE "osm_spouses" ADD "citizen_id" VARCHAR(13) NOT NULL UNIQUE;
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_osm_childre_citizen_170667" ON "osm_children" ("citizen_id");
        CREATE UNIQUE INDEX IF NOT EXISTS "uid_osm_spouses_citizen_193c35" ON "osm_spouses" ("citizen_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uid_osm_spouses_citizen_193c35";
        DROP INDEX IF EXISTS "uid_osm_childre_citizen_170667";
        ALTER TABLE "osm_children" DROP COLUMN "citizen_id";
        ALTER TABLE "osm_spouses" DROP COLUMN "citizen_id";"""
