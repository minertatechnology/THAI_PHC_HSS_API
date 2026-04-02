from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "positions" ADD COLUMN "scope_level" VARCHAR(30);
        CREATE INDEX IF NOT EXISTS "idx_positions_scope_level" ON "positions" ("scope_level");
        UPDATE "positions" SET "scope_level" = 'subdistrict' WHERE "position_code" = 'SHP';
        UPDATE "positions" SET "scope_level" = 'district' WHERE "position_code" = 'DPO';
        UPDATE "positions" SET "scope_level" = 'province' WHERE "position_code" = 'PPO';
        UPDATE "positions" SET "scope_level" = 'area' WHERE "position_code" = 'HA';
        UPDATE "positions" SET "scope_level" = 'country' WHERE "position_code" IN ('DIR', 'DHS');
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_positions_scope_level";
        ALTER TABLE "positions" DROP COLUMN IF EXISTS "scope_level";
    """
