from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "provinces" ADD COLUMN "quota" INT NOT NULL DEFAULT 0;
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "quota" INT NOT NULL DEFAULT 0;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "quota";
    ALTER TABLE "provinces" DROP COLUMN IF EXISTS "quota";
    """
