from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "osm_official_positions" ADD COLUMN "position_level" VARCHAR(20);
    CREATE INDEX IF NOT EXISTS "idx_osm_official_positions_position_level" ON "osm_official_positions" ("position_level");
    UPDATE "osm_official_positions" SET "position_level" = 'area' WHERE legacy_code = 40;
    UPDATE "osm_official_positions" SET "position_level" = 'region' WHERE legacy_code = 41;
    UPDATE "osm_official_positions" SET "position_level" = 'country' WHERE legacy_code = 42;

    CREATE TABLE IF NOT EXISTS "osm_benefit_claims" (
        "id" UUID NOT NULL PRIMARY KEY,
        "claim_type" VARCHAR(50) NOT NULL,
        "claim_date" DATE NOT NULL,
        "claim_round" INT,
        "amount" DECIMAL(12,2),
        "status" VARCHAR(30) NOT NULL,
        "decision_date" DATE,
        "paid_date" DATE,
        "note" TEXT,
        "created_by" VARCHAR(255) NOT NULL,
        "updated_by" VARCHAR(255),
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "deleted_at" TIMESTAMPTZ,
        "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS "idx_osm_benefit_claims_profile" ON "osm_benefit_claims" ("osm_profile_id");
    CREATE INDEX IF NOT EXISTS "idx_osm_benefit_claims_status" ON "osm_benefit_claims" ("status");
    CREATE INDEX IF NOT EXISTS "idx_osm_benefit_claims_date" ON "osm_benefit_claims" ("claim_date");

    CREATE TABLE IF NOT EXISTS "osm_awards" (
        "id" UUID NOT NULL PRIMARY KEY,
        "award_type" VARCHAR(50) NOT NULL,
        "award_name" VARCHAR(255),
        "award_code" VARCHAR(50),
        "awarded_date" DATE NOT NULL,
        "criteria" TEXT,
        "issuer" VARCHAR(255),
        "created_by" VARCHAR(255) NOT NULL,
        "updated_by" VARCHAR(255),
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        "deleted_at" TIMESTAMPTZ,
        "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS "idx_osm_awards_profile" ON "osm_awards" ("osm_profile_id");
    CREATE INDEX IF NOT EXISTS "idx_osm_awards_type" ON "osm_awards" ("award_type");
    CREATE INDEX IF NOT EXISTS "idx_osm_awards_code" ON "osm_awards" ("award_code");
    CREATE INDEX IF NOT EXISTS "idx_osm_awards_date" ON "osm_awards" ("awarded_date");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP INDEX IF EXISTS "idx_osm_awards_date";
    DROP INDEX IF EXISTS "idx_osm_awards_code";
    DROP INDEX IF EXISTS "idx_osm_awards_type";
    DROP INDEX IF EXISTS "idx_osm_awards_profile";
    DROP TABLE IF EXISTS "osm_awards";

    DROP INDEX IF EXISTS "idx_osm_benefit_claims_date";
    DROP INDEX IF EXISTS "idx_osm_benefit_claims_status";
    DROP INDEX IF EXISTS "idx_osm_benefit_claims_profile";
    DROP TABLE IF EXISTS "osm_benefit_claims";

    DROP INDEX IF EXISTS "idx_osm_official_positions_position_level";
    ALTER TABLE "osm_official_positions" DROP COLUMN IF EXISTS "position_level";
    """
