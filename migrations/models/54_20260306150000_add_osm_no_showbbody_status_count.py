from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "dashboard_annual_summary" ADD COLUMN "osm_no_showbbody_status_count" INT NOT NULL DEFAULT 0;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "dashboard_annual_summary" DROP COLUMN IF EXISTS "osm_no_showbbody_status_count";
    """
