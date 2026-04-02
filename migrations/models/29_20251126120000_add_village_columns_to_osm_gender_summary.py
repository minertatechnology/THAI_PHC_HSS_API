from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "osm_gender_summary"
        ADD COLUMN IF NOT EXISTS "village_code" VARCHAR(10),
        ADD COLUMN IF NOT EXISTS "village_no" VARCHAR(10),
        ADD COLUMN IF NOT EXISTS "village_name_th" VARCHAR(255);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "osm_gender_summary"
        DROP COLUMN IF EXISTS "village_code",
        DROP COLUMN IF EXISTS "village_no",
        DROP COLUMN IF EXISTS "village_name_th";
    """
