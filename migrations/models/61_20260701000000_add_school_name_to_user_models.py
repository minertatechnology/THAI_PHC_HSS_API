from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user"
            ADD COLUMN IF NOT EXISTS "school_name" VARCHAR(255);
        ALTER TABLE "people_user"
            ADD COLUMN IF NOT EXISTS "school_name" VARCHAR(255);
        ALTER TABLE "yuwa_osm_user"
            ADD COLUMN IF NOT EXISTS "school_name" VARCHAR(255);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "gen_h_user" DROP COLUMN IF EXISTS "school_name";
        ALTER TABLE "people_user" DROP COLUMN IF EXISTS "school_name";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN IF EXISTS "school_name";
    """
