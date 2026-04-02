from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        -- Add gen-h link fields to yuwa_osm_user
        ALTER TABLE "yuwa_osm_user"
            ADD COLUMN IF NOT EXISTS "gen_h_code" VARCHAR(20),
            ADD COLUMN IF NOT EXISTS "gen_h_id" UUID,
            ADD COLUMN IF NOT EXISTS "source_type" VARCHAR(20) NOT NULL DEFAULT 'new_registration';

        CREATE UNIQUE INDEX IF NOT EXISTS "idx_yuwa_osm_user_gen_h_code"
            ON "yuwa_osm_user" ("gen_h_code")
            WHERE "gen_h_code" IS NOT NULL;

        CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_user_gen_h_id"
            ON "yuwa_osm_user" ("gen_h_id");

        -- Seed GH69 counter from existing gen_h_user codes (idempotent)
        DO $$
        DECLARE
            v_max INTEGER;
        BEGIN
            SELECT COALESCE(MAX(CAST(SUBSTR(gen_h_code, 3) AS INTEGER)), 0)
            INTO v_max
            FROM gen_h_user
            WHERE gen_h_code ~ '^69[0-9]{6}$';

            INSERT INTO osm_code_counters (prefix, last_number)
            VALUES ('GH69', v_max)
            ON CONFLICT (prefix) DO NOTHING;
        END $$;

        -- Seed YW69 counter from existing yuwa_osm_code across both tables (idempotent)
        DO $$
        DECLARE
            v_max_yuwa BIGINT;
            v_max_people BIGINT;
            v_max BIGINT;
        BEGIN
            SELECT COALESCE(MAX(CAST(yuwa_osm_code AS BIGINT)), 0)
            INTO v_max_yuwa
            FROM yuwa_osm_user
            WHERE yuwa_osm_code ~ '^69[0-9]{7}$';

            SELECT COALESCE(MAX(CAST(yuwa_osm_code AS BIGINT)), 0)
            INTO v_max_people
            FROM people_user
            WHERE yuwa_osm_code ~ '^69[0-9]{7}$';

            v_max := GREATEST(v_max_yuwa, v_max_people);

            INSERT INTO osm_code_counters (prefix, last_number)
            VALUES ('YW69', v_max)
            ON CONFLICT (prefix) DO NOTHING;
        END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_yuwa_osm_user_gen_h_code";
        DROP INDEX IF EXISTS "idx_yuwa_osm_user_gen_h_id";

        ALTER TABLE "yuwa_osm_user"
            DROP COLUMN IF EXISTS "gen_h_code",
            DROP COLUMN IF EXISTS "gen_h_id",
            DROP COLUMN IF EXISTS "source_type";

        DELETE FROM "osm_code_counters" WHERE "prefix" IN ('GH69', 'YW69');
    """
