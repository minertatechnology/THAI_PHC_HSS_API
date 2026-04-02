from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE IF NOT EXISTS "dashboard_annual_summary" (
        "id" UUID NOT NULL PRIMARY KEY,
        "year_buddhist" INT NOT NULL,
        "province_code" VARCHAR(10),
        "province_name_th" VARCHAR(255),
        "province_name_en" VARCHAR(255),
        "district_count" INT NOT NULL DEFAULT 0,
        "subdistrict_count" INT NOT NULL DEFAULT 0,
        "village_count" INT NOT NULL DEFAULT 0,
        "community_count" INT NOT NULL DEFAULT 0,
        "pcu_count" INT NOT NULL DEFAULT 0,
        "hosp_satang_count" INT NOT NULL DEFAULT 0,
        "hosp_general_count" INT NOT NULL DEFAULT 0,
        "osm_count" INT NOT NULL DEFAULT 0,
        "osm_allowance_eligible_count" INT NOT NULL DEFAULT 0,
        "osm_training_budget_count" INT NOT NULL DEFAULT 0,
        "osm_payment_training_count" INT NOT NULL DEFAULT 0,
        "last_calculated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS "idx_dashboard_sum_year" ON "dashboard_annual_summary" ("year_buddhist");
    CREATE INDEX IF NOT EXISTS "idx_dashboard_sum_year_province" ON "dashboard_annual_summary" ("year_buddhist", "province_code");
    CREATE UNIQUE INDEX IF NOT EXISTS "uid_dashboard_sum_year_province" ON "dashboard_annual_summary" ("year_buddhist", "province_code");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP TABLE IF EXISTS "dashboard_annual_summary";
    """
