from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "news_articles" (
    "id" UUID NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "department" VARCHAR(255) NOT NULL,
    "content_html" TEXT NOT NULL,
    "image_urls" JSONB NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_news_articl_title_3aea20" ON "news_articles" ("title");
CREATE INDEX IF NOT EXISTS "idx_news_articl_departm_966eb6" ON "news_articles" ("department");
CREATE INDEX IF NOT EXISTS "idx_news_articl_created_8bfcb8" ON "news_articles" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_news_articl_updated_7dcc8b" ON "news_articles" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_news_articl_created_99a519" ON "news_articles" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_news_articl_updated_4d518f" ON "news_articles" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_news_articl_deleted_54001d" ON "news_articles" ("deleted_at");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "news_articles";"""
