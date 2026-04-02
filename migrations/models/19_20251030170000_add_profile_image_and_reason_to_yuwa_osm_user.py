from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "yuwa_osm_user" ADD "profile_image" VARCHAR(1024);
        ALTER TABLE "yuwa_osm_user" ADD "registration_reason" TEXT;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "yuwa_osm_user" DROP COLUMN "profile_image";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN "registration_reason";
    """
