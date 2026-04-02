from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "approval_status" VARCHAR(8) NOT NULL DEFAULT 'pending';
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "approved_by" UUID;
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "approved_at" TIMESTAMPTZ;
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "rejected_by" UUID;
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "rejected_at" TIMESTAMPTZ;
        ALTER TABLE "yuwa_osm_user" ADD COLUMN IF NOT EXISTS "rejection_reason" TEXT;
        ALTER TABLE "yuwa_osm_user" ALTER COLUMN "is_active" SET DEFAULT False;
        UPDATE "yuwa_osm_user" SET "approval_status" = CASE WHEN "is_active" = True THEN 'approved' ELSE 'pending' END WHERE "approval_status" IS NULL OR "approval_status" = '';
        CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_approved_by" ON "yuwa_osm_user" ("approved_by");
        CREATE INDEX IF NOT EXISTS "idx_yuwa_osm_us_rejected_by" ON "yuwa_osm_user" ("rejected_by");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_yuwa_osm_us_rejected_by";
        DROP INDEX IF EXISTS "idx_yuwa_osm_us_approved_by";
        ALTER TABLE "yuwa_osm_user" ALTER COLUMN "is_active" SET DEFAULT True;
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "rejection_reason";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "rejected_at";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "rejected_by";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "approved_at";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "approved_by";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "approval_status";
    """
