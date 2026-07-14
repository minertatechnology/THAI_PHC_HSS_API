from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "health_service_areas" (
            "id" UUID NOT NULL PRIMARY KEY,
            "health_service_id" VARCHAR(255) NOT NULL REFERENCES "health_services" ("health_service_code") ON DELETE CASCADE,
            "subdistrict_id" VARCHAR(255) NOT NULL REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE,
            "village_nos" JSONB,
            "is_primary" BOOL NOT NULL DEFAULT FALSE,
            "created_by" UUID NOT NULL,
            "updated_by" UUID,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "deleted_at" TIMESTAMPTZ,
            CONSTRAINT "uniq_healthsvcarea_healthsvc_subdist" UNIQUE ("health_service_id", "subdistrict_id")
        );
        CREATE INDEX IF NOT EXISTS "idx_healthsvcarea_health_service_id" ON "health_service_areas" ("health_service_id");
        CREATE INDEX IF NOT EXISTS "idx_healthsvcarea_subdistrict_id" ON "health_service_areas" ("subdistrict_id");
        CREATE INDEX IF NOT EXISTS "idx_healthsvcarea_is_primary" ON "health_service_areas" ("is_primary");

        -- Data migration: ดึง subdistrict_id + village_no เดิมจาก health_services -> สร้าง record is_primary=True
        INSERT INTO "health_service_areas" ("id", "health_service_id", "subdistrict_id", "village_nos", "is_primary", "created_by", "created_at", "updated_at")
        SELECT
            gen_random_uuid(),
            hs."health_service_code",
            hs."subdistrict_id",
            CASE WHEN hs."village_no" IS NOT NULL AND hs."village_no" <> '' THEN jsonb_build_array(hs."village_no") ELSE NULL END,
            TRUE,
            COALESCE(hs."created_by", '00000000-0000-0000-0000-000000000000'::uuid),
            COALESCE(hs."created_at", CURRENT_TIMESTAMP),
            CURRENT_TIMESTAMP
        FROM "health_services" hs
        WHERE hs."subdistrict_id" IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM "health_service_areas" hsa
              WHERE hsa."health_service_id" = hs."health_service_code"
                AND hsa."subdistrict_id" = hs."subdistrict_id"
          );
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_healthsvcarea_is_primary";
        DROP INDEX IF EXISTS "idx_healthsvcarea_subdistrict_id";
        DROP INDEX IF EXISTS "idx_healthsvcarea_health_service_id";
        DROP TABLE IF EXISTS "health_service_areas";
    """
