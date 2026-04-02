from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE IF NOT EXISTS "osm_status_history" (
        "id" UUID NOT NULL PRIMARY KEY,
        "previous_osm_status" VARCHAR(10),
        "new_osm_status" VARCHAR(10),
        "previous_is_active" BOOL,
        "new_is_active" BOOL NOT NULL,
        "previous_approval_status" VARCHAR(20),
        "new_approval_status" VARCHAR(20),
        "province_code" VARCHAR(6),
        "district_code" VARCHAR(8),
        "subdistrict_code" VARCHAR(10),
        "village_no" VARCHAR(10),
        "retirement_reason" VARCHAR(50),
        "remark" VARCHAR(500),
        "changed_by" UUID NOT NULL,
        "changed_by_name" VARCHAR(100),
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS "idx_osh_osm_profile" ON "osm_status_history" ("osm_profile_id");
    CREATE INDEX IF NOT EXISTS "idx_osh_changed_by" ON "osm_status_history" ("changed_by");
    CREATE INDEX IF NOT EXISTS "idx_osh_province" ON "osm_status_history" ("province_code");
    CREATE INDEX IF NOT EXISTS "idx_osh_created_at" ON "osm_status_history" ("created_at");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP TABLE IF EXISTS "osm_status_history";
    """
