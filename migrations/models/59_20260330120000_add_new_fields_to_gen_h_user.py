from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user"
            ADD COLUMN IF NOT EXISTS "citizen_id" VARCHAR(13),
            ADD COLUMN IF NOT EXISTS "birthday" DATE,
            ADD COLUMN IF NOT EXISTS "organization" VARCHAR(255),
            ADD COLUMN IF NOT EXISTS "registration_reason" TEXT,
            ADD COLUMN IF NOT EXISTS "photo_1inch" VARCHAR(1024),
            ADD COLUMN IF NOT EXISTS "attachments" JSONB;
        CREATE INDEX IF NOT EXISTS "idx_gen_h_user_citizen_id" ON "gen_h_user" ("citizen_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_gen_h_user_citizen_id";
        ALTER TABLE "gen_h_user"
            DROP COLUMN IF EXISTS "citizen_id",
            DROP COLUMN IF EXISTS "birthday",
            DROP COLUMN IF EXISTS "organization",
            DROP COLUMN IF EXISTS "registration_reason",
            DROP COLUMN IF EXISTS "photo_1inch",
            DROP COLUMN IF EXISTS "attachments";
    """
