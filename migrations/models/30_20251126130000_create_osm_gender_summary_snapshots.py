from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "osm_gender_summary"
        ADD COLUMN IF NOT EXISTS "snapshot_type" VARCHAR(20) NOT NULL DEFAULT 'live',
        ADD COLUMN IF NOT EXISTS "fiscal_year" INT,
        ADD COLUMN IF NOT EXISTS "captured_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ADD COLUMN IF NOT EXISTS "triggered_by" VARCHAR(255),
        ADD COLUMN IF NOT EXISTS "note" TEXT;

    CREATE INDEX IF NOT EXISTS "idx_osm_gender_summary_snapshot_type"
        ON "osm_gender_summary" ("snapshot_type");

    CREATE INDEX IF NOT EXISTS "idx_osm_gender_summary_snapshot_year"
        ON "osm_gender_summary" ("snapshot_type", "fiscal_year", "province_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "osm_gender_summary"
        DROP COLUMN IF EXISTS "snapshot_type",
        DROP COLUMN IF EXISTS "fiscal_year",
        DROP COLUMN IF EXISTS "captured_at",
        DROP COLUMN IF EXISTS "triggered_by",
        DROP COLUMN IF EXISTS "note";
    """
