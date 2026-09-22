from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- ระดับของตำแหน่งชมรม อสม. (ใช้ตัดสินเงื่อนไขอายุงานขั้นต่ำ + จัดกลุ่ม/เรียงในรายงานประธาน)
        ALTER TABLE "osm_club_positions" ADD COLUMN IF NOT EXISTS "position_level" VARCHAR(20);
        CREATE INDEX IF NOT EXISTS "idx_osm_club_positions_position_level" ON "osm_club_positions" ("position_level");

        -- เติมระดับให้ข้อมูลเดิมจากชื่อตำแหน่ง (เช่น "ประธานชมรม อสม. ระดับตำบล" -> subdistrict)
        UPDATE "osm_club_positions"
        SET "position_level" = CASE
            WHEN "position_name_th" LIKE '%หมู่บ้าน%' THEN 'village'
            WHEN "position_name_th" LIKE '%ตำบล%' THEN 'subdistrict'
            WHEN "position_name_th" LIKE '%อำเภอ%' THEN 'district'
            WHEN "position_name_th" LIKE '%จังหวัด%' THEN 'province'
            WHEN "position_name_th" LIKE '%เขต%' THEN 'area'
            WHEN "position_name_th" LIKE '%ภาค%' THEN 'region'
            WHEN "position_name_th" LIKE '%ประเทศ%' OR "position_name_th" LIKE '%ชาติ%' THEN 'country'
            ELSE NULL
        END
        WHERE "position_level" IS NULL;

        -- วาระ / วันที่ได้รับการคัดเลือก / ไฟล์แนบ ของแต่ละรายการตำแหน่งชมรม
        ALTER TABLE "osm_profile_club_positions"
            ADD COLUMN IF NOT EXISTS "term_start_year" INT,
            ADD COLUMN IF NOT EXISTS "term_end_year" INT,
            ADD COLUMN IF NOT EXISTS "appointed_date" DATE,
            ADD COLUMN IF NOT EXISTS "image_path" VARCHAR(1024),
            ADD COLUMN IF NOT EXISTS "certificate_path" VARCHAR(1024);
        CREATE INDEX IF NOT EXISTS "idx_osm_profile_club_positions_term_start" ON "osm_profile_club_positions" ("term_start_year");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_osm_profile_club_positions_term_start";
        ALTER TABLE "osm_profile_club_positions"
            DROP COLUMN IF EXISTS "certificate_path",
            DROP COLUMN IF EXISTS "image_path",
            DROP COLUMN IF EXISTS "appointed_date",
            DROP COLUMN IF EXISTS "term_end_year",
            DROP COLUMN IF EXISTS "term_start_year";
        DROP INDEX IF EXISTS "idx_osm_club_positions_position_level";
        ALTER TABLE "osm_club_positions" DROP COLUMN IF EXISTS "position_level";
    """
