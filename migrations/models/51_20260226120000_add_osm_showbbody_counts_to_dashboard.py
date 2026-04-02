from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "osm_showbbody_paid_count" INT NOT NULL DEFAULT 0;
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "osm_showbbody_not_paid_count" INT NOT NULL DEFAULT 0;
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "osm_showbbody_pending_count" INT NOT NULL DEFAULT 0;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "osm_showbbody_paid_count";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "osm_showbbody_not_paid_count";
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "osm_showbbody_pending_count";
    """
