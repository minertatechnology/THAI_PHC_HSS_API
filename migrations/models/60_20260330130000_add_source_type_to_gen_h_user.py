from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user"
            ADD COLUMN IF NOT EXISTS "source_type" VARCHAR(20) NOT NULL DEFAULT 'migration';
        UPDATE "gen_h_user" SET "source_type" = 'migration' WHERE "source_type" = 'migration';
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user" DROP COLUMN IF EXISTS "source_type";
    """
