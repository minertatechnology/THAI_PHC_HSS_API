from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "mobile_banners" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "subtitle" TEXT,
    "image_url" VARCHAR(1024) NOT NULL,
    "target_url" VARCHAR(1024),
    "order_index" INT NOT NULL DEFAULT 0,
    "platforms" JSONB NOT NULL,
    "metadata" JSONB,
    "starts_at" TIMESTAMPTZ,
    "ends_at" TIMESTAMPTZ,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_by" UUID,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mobile_bann_order_i_162064" ON "mobile_banners" ("order_index");
CREATE INDEX IF NOT EXISTS "idx_mobile_bann_starts__14b707" ON "mobile_banners" ("starts_at");
CREATE INDEX IF NOT EXISTS "idx_mobile_bann_ends_at_38fdb3" ON "mobile_banners" ("ends_at");
CREATE INDEX IF NOT EXISTS "idx_mobile_bann_is_acti_dedd9f" ON "mobile_banners" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_mobile_bann_created_35a15b" ON "mobile_banners" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_mobile_bann_updated_1d9ae1" ON "mobile_banners" ("updated_by");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "mobile_banners";"""
