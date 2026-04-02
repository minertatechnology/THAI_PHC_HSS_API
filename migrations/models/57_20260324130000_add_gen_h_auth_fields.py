from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user" ADD COLUMN IF NOT EXISTS "password_hash" VARCHAR(255);
        ALTER TABLE "gen_h_user" ADD COLUMN IF NOT EXISTS "is_first_login" BOOL NOT NULL DEFAULT TRUE;
        ALTER TABLE "gen_h_user" ADD COLUMN IF NOT EXISTS "password_attempts" INT NOT NULL DEFAULT 0;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user" DROP COLUMN IF EXISTS "password_hash";
        ALTER TABLE "gen_h_user" DROP COLUMN IF EXISTS "is_first_login";
        ALTER TABLE "gen_h_user" DROP COLUMN IF EXISTS "password_attempts";
    """
