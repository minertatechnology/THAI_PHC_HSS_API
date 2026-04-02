from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "osm_code_counters" (
            "prefix" VARCHAR(32) NOT NULL PRIMARY KEY,
            "last_number" INT NOT NULL DEFAULT 0,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS "idx_osm_code_counters_prefix" ON "osm_code_counters" ("prefix");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "osm_code_counters";
    """
