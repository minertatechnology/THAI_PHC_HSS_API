from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" ADD "is_first_login" BOOLEAN NOT NULL DEFAULT True;
        ALTER TABLE "officers" ADD "password_hash" VARCHAR(255);
        CREATE TABLE IF NOT EXISTS "yuwa_osm_user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "prefix" VARCHAR(50),
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(100) NOT NULL,
    "citizen_id" VARCHAR(13) UNIQUE,
    "gender" VARCHAR(10),
    "phone_number" VARCHAR(20) NOT NULL UNIQUE,
    "email" VARCHAR(255),
    "line_id" VARCHAR(100),
    "school_or_org" VARCHAR(255),
    "province_code" VARCHAR(10),
    "province_name" VARCHAR(255),
    "district_code" VARCHAR(10),
    "district_name" VARCHAR(255),
    "subdistrict_code" VARCHAR(10),
    "subdistrict_name" VARCHAR(255),
    "birthday" DATE,
    "password_hash" VARCHAR(255),
    "is_first_login" BOOLEAN NOT NULL DEFAULT True,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_citizen_aa8ed6" ON "yuwa_osm_user" ("citizen_id");
CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_phone_n_e7d5d3" ON "yuwa_osm_user" ("phone_number");
CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_email_12c0e8" ON "yuwa_osm_user" ("email");
CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_provinc_e288d4" ON "yuwa_osm_user" ("province_code");
CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_distric_3efaba" ON "yuwa_osm_user" ("district_code");
CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_subdist_8d96e6" ON "yuwa_osm_user" ("subdistrict_code");
COMMENT ON TABLE "yuwa_osm_user" IS 'Central Yuwa member profile persisted for unified SSO.';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" DROP COLUMN "is_first_login";
        ALTER TABLE "officers" DROP COLUMN "password_hash";
        DROP TABLE IF EXISTS "yuwa_osm_user";"""
