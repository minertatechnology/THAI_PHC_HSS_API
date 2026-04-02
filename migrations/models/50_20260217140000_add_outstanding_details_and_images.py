from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "osm_outstandings" ADD IF NOT EXISTS "title" VARCHAR(500);
        ALTER TABLE "osm_outstandings" ADD IF NOT EXISTS "description" TEXT;
        ALTER TABLE "osm_outstandings" ALTER COLUMN "award_level_id" DROP NOT NULL;
        ALTER TABLE "osm_outstandings" ADD IF NOT EXISTS "award_category_id" UUID REFERENCES "award_categories" ("id") ON DELETE SET NULL;

        CREATE TABLE IF NOT EXISTS "osm_outstanding_images" (
            "id" UUID NOT NULL PRIMARY KEY,
            "outstanding_id" UUID NOT NULL REFERENCES "osm_outstandings" ("id") ON DELETE CASCADE,
            "image_url" VARCHAR(1024) NOT NULL,
            "sort_order" INT NOT NULL DEFAULT 0,
            "caption" VARCHAR(500),
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS "idx_osm_outstanding_images_outstanding" ON "osm_outstanding_images" ("outstanding_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "osm_outstanding_images";
        ALTER TABLE "osm_outstandings" DROP COLUMN IF EXISTS "award_category_id";
        ALTER TABLE "osm_outstandings" DROP COLUMN IF EXISTS "description";
        ALTER TABLE "osm_outstandings" DROP COLUMN IF EXISTS "title";
    """
