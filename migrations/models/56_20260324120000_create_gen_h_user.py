from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "gen_h_user" (
            "id" UUID NOT NULL PRIMARY KEY,
            "gen_h_code" VARCHAR(20) NOT NULL UNIQUE,
            "prefix" VARCHAR(50),
            "first_name" VARCHAR(100) NOT NULL,
            "last_name" VARCHAR(100) NOT NULL,
            "gender" VARCHAR(10),
            "phone_number" VARCHAR(20),
            "email" VARCHAR(255),
            "line_id" VARCHAR(100),
            "school" VARCHAR(255),
            "province_code" VARCHAR(10),
            "province_name" VARCHAR(255),
            "district_code" VARCHAR(10),
            "district_name" VARCHAR(255),
            "subdistrict_code" VARCHAR(10),
            "subdistrict_name" VARCHAR(255),
            "profile_image_url" VARCHAR(1024),
            "member_card_url" VARCHAR(1024),
            "points" INT NOT NULL DEFAULT 0,
            "is_active" BOOL NOT NULL DEFAULT TRUE,
            "people_user_id" UUID,
            "yuwa_osm_user_id" UUID,
            "transferred_at" TIMESTAMPTZ,
            "created_by" VARCHAR(255),
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_gen_h_code" ON "gen_h_user" ("gen_h_code");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_phone_number" ON "gen_h_user" ("phone_number");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_email" ON "gen_h_user" ("email");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_province_code" ON "gen_h_user" ("province_code");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_district_code" ON "gen_h_user" ("district_code");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_subdistrict_code" ON "gen_h_user" ("subdistrict_code");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_people_user_id" ON "gen_h_user" ("people_user_id");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_yuwa_osm_user_id" ON "gen_h_user" ("yuwa_osm_user_id");
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_created_by" ON "gen_h_user" ("created_by");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "gen_h_user";
    """
