from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_profiles" ADD "password_attempts" INT NOT NULL DEFAULT 0;
        ALTER TABLE "yuwa_osm_user" ADD "password_attempts" INT NOT NULL DEFAULT 0;
        ALTER TABLE "people_user" ADD "password_attempts" INT NOT NULL DEFAULT 0;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_profiles" DROP COLUMN "password_attempts";
        ALTER TABLE "yuwa_osm_user" DROP COLUMN "password_attempts";
        ALTER TABLE "people_user" DROP COLUMN "password_attempts";
    """
