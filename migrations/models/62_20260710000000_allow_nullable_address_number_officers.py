from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" ALTER COLUMN "address_number" DROP NOT NULL;
        ALTER TABLE "osm_profiles" ALTER COLUMN "address_number" DROP NOT NULL;
        ALTER TABLE "osm_spouses" ALTER COLUMN "address_number" DROP NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "address_number" DROP NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE "officers" SET "address_number" = '' WHERE "address_number" IS NULL;
        UPDATE "osm_profiles" SET "address_number" = '' WHERE "address_number" IS NULL;
        UPDATE "osm_spouses" SET "address_number" = '' WHERE "address_number" IS NULL;
        UPDATE "osm_children" SET "address_number" = '' WHERE "address_number" IS NULL;

        ALTER TABLE "officers" ALTER COLUMN "address_number" SET NOT NULL;
        ALTER TABLE "osm_profiles" ALTER COLUMN "address_number" SET NOT NULL;
        ALTER TABLE "osm_spouses" ALTER COLUMN "address_number" SET NOT NULL;
        ALTER TABLE "osm_children" ALTER COLUMN "address_number" SET NOT NULL;
    """
