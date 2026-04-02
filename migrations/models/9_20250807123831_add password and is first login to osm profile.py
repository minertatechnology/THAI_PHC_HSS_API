from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_profiles" ADD "password_hash" VARCHAR(255);
        ALTER TABLE "osm_profiles" ADD "is_first_login" BOOL NOT NULL DEFAULT True;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_profiles" DROP COLUMN "password_hash";
        ALTER TABLE "osm_profiles" DROP COLUMN "is_first_login";"""
