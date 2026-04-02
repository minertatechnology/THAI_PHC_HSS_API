from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_officers_user_cr_1a880e";
        ALTER TABLE "officers" DROP CONSTRAINT IF EXISTS "fk_officers_user_cre_88cf2684";
        ALTER TABLE "officers" DROP COLUMN "user_credential_id";
        CREATE TABLE IF NOT EXISTS "osm_positions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "position_name_th" VARCHAR(255) NOT NULL,
    "position_name_en" VARCHAR(255),
    "position_level" VARCHAR(11) NOT NULL,
    "legacy_id" INT,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_osm_positio_positio_7135cc" ON "osm_positions" ("position_name_th");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_positio_fc7ce3" ON "osm_positions" ("position_level");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_created_2cd964" ON "osm_positions" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_updated_5d7197" ON "osm_positions" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_created_99eef1" ON "osm_positions" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_updated_aed850" ON "osm_positions" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_deleted_5151ae" ON "osm_positions" ("deleted_at");
COMMENT ON COLUMN "osm_positions"."position_level" IS 'VILLAGE: village\nSUBDISTRICT: subdistrict\nDISTRICT: district\nPROVINCE: province\nAREA: area\nREGION: region\nCOUNTRY: country';
        CREATE TABLE IF NOT EXISTS "osm_position_confirmations" (
    "id" UUID NOT NULL PRIMARY KEY,
    "allowance_confirmation_status" VARCHAR(27) NOT NULL DEFAULT 'not_confirmed',
    "created_by" VARCHAR(255) NOT NULL,
    "updated_by" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_positio_created_28b111" ON "osm_position_confirmations" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_updated_3ce952" ON "osm_position_confirmations" ("updated_by");
COMMENT ON COLUMN "osm_position_confirmations"."allowance_confirmation_status" IS 'สถานะการยืนยันสิทธิ์เงินค่าป่วยการ';
COMMENT ON TABLE "osm_position_confirmations" IS 'ตารางการยืนยันตำแหน่งและสิทธิ์เงินค่าป่วยการ อสม.';
        CREATE TABLE IF NOT EXISTS "osm_position_confirmation_positions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_by" VARCHAR(255) NOT NULL,
    "updated_by" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "osm_position_id" UUID NOT NULL REFERENCES "osm_positions" ("id") ON DELETE CASCADE,
    "position_confirmation_id" UUID NOT NULL REFERENCES "osm_position_confirmations" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_positio_created_b8e193" ON "osm_position_confirmation_positions" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_positio_updated_865586" ON "osm_position_confirmation_positions" ("updated_by");
COMMENT ON TABLE "osm_position_confirmation_positions" IS 'ตารางเชื่อมโยงระหว่าง OsmPositionConfirmation และ LeadershipPosition (Many-to-Many)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" ADD "user_credential_id" UUID NOT NULL;
        DROP TABLE IF EXISTS "osm_position_confirmation_positions";
        DROP TABLE IF EXISTS "osm_position_confirmations";
        DROP TABLE IF EXISTS "osm_positions";
        ALTER TABLE "officers" ADD CONSTRAINT "fk_officers_user_cre_88cf2684" FOREIGN KEY ("user_credential_id") REFERENCES "user_credentials" ("id") ON DELETE CASCADE;
        CREATE INDEX IF NOT EXISTS "idx_officers_user_cr_1a880e" ON "officers" ("user_credential_id");"""
