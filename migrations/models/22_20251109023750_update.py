from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "villages" (
    "village_code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "village_no" INT,
    "village_name_th" VARCHAR(255) NOT NULL,
    "village_name_en" VARCHAR(255),
    "metro_status" VARCHAR(50),
    "government_id" VARCHAR(50),
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "external_url" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "health_service_id" VARCHAR(255) REFERENCES "health_services" ("health_service_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) NOT NULL REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_villages_village_55627e" ON "villages" ("village_no");
CREATE INDEX IF NOT EXISTS "idx_villages_governm_01e3e0" ON "villages" ("government_id");
COMMENT ON TABLE "villages" IS 'ตารางข้อมูลหมู่บ้าน (legacy villcode-based records).';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "villages";"""
