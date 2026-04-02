from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "geography_level" VARCHAR(20) NOT NULL DEFAULT 'province';
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "district_code" VARCHAR(10);
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "district_name_th" VARCHAR(255);
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "district_name_en" VARCHAR(255);
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "subdistrict_code" VARCHAR(10);
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "subdistrict_name_th" VARCHAR(255);
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "subdistrict_name_en" VARCHAR(255);
    DROP INDEX IF EXISTS "idx_dashboard_sum_year_province";
    DROP INDEX IF EXISTS "uid_dashboard_sum_year_province";
    CREATE INDEX IF NOT EXISTS "idx_dashboard_sum_year_geo_province" ON "dashboard_annual_summary" ("year_buddhist", "geography_level", "province_code");
    CREATE INDEX IF NOT EXISTS "idx_dashboard_sum_year_geo_district" ON "dashboard_annual_summary" ("year_buddhist", "geography_level", "district_code");
    CREATE INDEX IF NOT EXISTS "idx_dashboard_sum_year_geo_subdistrict" ON "dashboard_annual_summary" ("year_buddhist", "geography_level", "subdistrict_code");
    CREATE UNIQUE INDEX IF NOT EXISTS "uid_dashboard_sum_geo_scope" ON "dashboard_annual_summary" ("year_buddhist", "geography_level", "province_code", "district_code", "subdistrict_code");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP INDEX IF EXISTS "idx_dashboard_sum_year_geo_province";
    DROP INDEX IF EXISTS "idx_dashboard_sum_year_geo_district";
    DROP INDEX IF EXISTS "idx_dashboard_sum_year_geo_subdistrict";
    DROP INDEX IF EXISTS "uid_dashboard_sum_geo_scope";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "subdistrict_name_en";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "subdistrict_name_th";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "subdistrict_code";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "district_name_en";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "district_name_th";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "district_code";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "geography_level";
    CREATE INDEX IF NOT EXISTS "idx_dashboard_sum_year_province" ON "dashboard_annual_summary" ("year_buddhist", "province_code");
    CREATE UNIQUE INDEX IF NOT EXISTS "uid_dashboard_sum_year_province" ON "dashboard_annual_summary" ("year_buddhist", "province_code");
    """
