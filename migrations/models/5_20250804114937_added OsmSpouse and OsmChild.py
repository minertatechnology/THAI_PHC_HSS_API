from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "osm_children" (
    "id" UUID NOT NULL PRIMARY KEY,
    "order_of_children" INT,
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(100) NOT NULL,
    "phone" VARCHAR(50),
    "email" VARCHAR(255),
    "gender" VARCHAR(6) NOT NULL DEFAULT 'other',
    "birth_date" DATE,
    "blood_type" VARCHAR(7) NOT NULL DEFAULT 'other',
    "address_number" VARCHAR(100) NOT NULL,
    "alley" VARCHAR(255),
    "street" VARCHAR(255),
    "village_no" VARCHAR(10),
    "village_name" VARCHAR(255),
    "village_code" VARCHAR(10),
    "postal_code" VARCHAR(10),
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "district_id" VARCHAR(255) NOT NULL REFERENCES "districts" ("district_code") ON DELETE CASCADE,
    "education_id" UUID NOT NULL REFERENCES "educations" ("id") ON DELETE CASCADE,
    "occupation_id" UUID NOT NULL REFERENCES "occupations" ("id") ON DELETE CASCADE,
    "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE,
    "prefix_id" UUID NOT NULL REFERENCES "prefixes" ("id") ON DELETE CASCADE,
    "province_id" VARCHAR(255) NOT NULL REFERENCES "provinces" ("province_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) NOT NULL REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_childre_birth_d_0e84b1" ON "osm_children" ("birth_date");
CREATE INDEX IF NOT EXISTS "idx_osm_childre_created_226964" ON "osm_children" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_childre_updated_623356" ON "osm_children" ("updated_by");
COMMENT ON COLUMN "osm_children"."gender" IS 'MALE: male\nFEMALE: female\nOTHER: other';
COMMENT ON COLUMN "osm_children"."blood_type" IS 'A: A\nB: B\nAB: AB\nO: O\nOTHER: other\nUNKNOWN: unknown';
        CREATE TABLE IF NOT EXISTS "osm_spouses" (
    "id" UUID NOT NULL PRIMARY KEY,
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(100) NOT NULL,
    "phone" VARCHAR(50),
    "email" VARCHAR(255),
    "gender" VARCHAR(6) NOT NULL DEFAULT 'other',
    "birth_date" DATE,
    "blood_type" VARCHAR(7) NOT NULL DEFAULT 'other',
    "address_number" VARCHAR(100) NOT NULL,
    "alley" VARCHAR(255),
    "street" VARCHAR(255),
    "village_no" VARCHAR(10),
    "village_name" VARCHAR(255),
    "village_code" VARCHAR(10),
    "postal_code" VARCHAR(10),
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "district_id" VARCHAR(255) NOT NULL REFERENCES "districts" ("district_code") ON DELETE CASCADE,
    "education_id" UUID NOT NULL REFERENCES "educations" ("id") ON DELETE CASCADE,
    "occupation_id" UUID NOT NULL REFERENCES "occupations" ("id") ON DELETE CASCADE,
    "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE,
    "prefix_id" UUID NOT NULL REFERENCES "prefixes" ("id") ON DELETE CASCADE,
    "province_id" VARCHAR(255) NOT NULL REFERENCES "provinces" ("province_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) NOT NULL REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_spouses_birth_d_a9772e" ON "osm_spouses" ("birth_date");
CREATE INDEX IF NOT EXISTS "idx_osm_spouses_created_06ca11" ON "osm_spouses" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_spouses_updated_1ef446" ON "osm_spouses" ("updated_by");
COMMENT ON COLUMN "osm_spouses"."gender" IS 'MALE: male\nFEMALE: female\nOTHER: other';
COMMENT ON COLUMN "osm_spouses"."blood_type" IS 'A: A\nB: B\nAB: AB\nO: O\nOTHER: other\nUNKNOWN: unknown';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "osm_children";
        DROP TABLE IF EXISTS "osm_spouses";"""
