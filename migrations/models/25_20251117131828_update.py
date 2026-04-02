from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_children" ALTER COLUMN "occupation_id" DROP NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "education_id" DROP NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "blood_type" DROP DEFAULT;
        ALTER TABLE "osm_children" ALTER COLUMN "blood_type" DROP NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_children" ALTER COLUMN "occupation_id" SET NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "education_id" SET NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "blood_type" SET NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "blood_type" SET DEFAULT 'other';"""
