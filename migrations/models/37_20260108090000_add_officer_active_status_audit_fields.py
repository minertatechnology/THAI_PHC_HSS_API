from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "officers" ADD COLUMN IF NOT EXISTS "active_status_at" TIMESTAMPTZ;
    ALTER TABLE "officers" ADD COLUMN IF NOT EXISTS "active_status_by" UUID;
    CREATE INDEX IF NOT EXISTS "idx_officers_active_status_by" ON "officers" ("active_status_by");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP INDEX IF EXISTS "idx_officers_active_status_by";
    ALTER TABLE "officers" DROP COLUMN IF EXISTS "active_status_by";
    ALTER TABLE "officers" DROP COLUMN IF EXISTS "active_status_at";
    """
