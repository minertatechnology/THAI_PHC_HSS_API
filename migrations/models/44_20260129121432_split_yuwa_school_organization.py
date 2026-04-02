from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "school" VARCHAR(255);
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "organization" VARCHAR(255);
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'yuwa_osm_user'
                  AND column_name = 'school_or_org'
            ) THEN
                UPDATE "yuwa_osm_user"
                SET "school" = COALESCE("school", "school_or_org"),
                    "organization" = COALESCE("organization", "school_or_org")
                WHERE "school_or_org" IS NOT NULL;
                ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "school_or_org";
            END IF;
        END $$;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "school_or_org" VARCHAR(255);
        UPDATE "yuwa_osm_user"
        SET "school_or_org" = COALESCE("school", "organization")
        WHERE "school_or_org" IS NULL;
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "school";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "organization";
    """
