from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "people_user" (
            "id" UUID NOT NULL PRIMARY KEY,
            "citizen_id" VARCHAR(13) NOT NULL UNIQUE,
            "first_name" VARCHAR(100) NOT NULL,
            "last_name" VARCHAR(100) NOT NULL,
            "gender" VARCHAR(10),
            "phone_number" VARCHAR(20),
            "email" VARCHAR(255),
            "province_code" VARCHAR(10),
            "province_name" VARCHAR(255),
            "district_code" VARCHAR(10),
            "district_name" VARCHAR(255),
            "subdistrict_code" VARCHAR(10),
            "subdistrict_name" VARCHAR(255),
            "birthday" DATE,
            "password_hash" VARCHAR(255),
            "is_first_login" BOOL NOT NULL DEFAULT TRUE,
            "is_active" BOOL NOT NULL DEFAULT FALSE,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_people_user_phone" ON "people_user" ("phone_number");
        CREATE INDEX IF NOT EXISTS "idx_people_user_email" ON "people_user" ("email");
        CREATE INDEX IF NOT EXISTS "idx_people_user_province" ON "people_user" ("province_code");
        CREATE INDEX IF NOT EXISTS "idx_people_user_district" ON "people_user" ("district_code");
        CREATE INDEX IF NOT EXISTS "idx_people_user_subdistrict" ON "people_user" ("subdistrict_code");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "people_user";
    """
