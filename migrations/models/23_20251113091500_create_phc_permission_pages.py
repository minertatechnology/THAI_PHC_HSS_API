from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE IF NOT EXISTS "phc_permission_page" (
        "id" UUID NOT NULL PRIMARY KEY,
        "system_name" VARCHAR(100) NOT NULL,
        "main_menu" VARCHAR(255) NOT NULL,
        "sub_main_menu" VARCHAR(255),
        "allowed_levels" JSONB NOT NULL DEFAULT '[]'::jsonb,
        "is_active" BOOL NOT NULL DEFAULT TRUE,
        "display_order" INT NOT NULL DEFAULT 0,
        "metadata" JSONB,
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE UNIQUE INDEX IF NOT EXISTS "uid_permission_page_key" ON "phc_permission_page" ("system_name", "main_menu", "sub_main_menu");
    CREATE INDEX IF NOT EXISTS "idx_permission_page_system" ON "phc_permission_page" ("system_name");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP TABLE IF EXISTS "phc_permission_page";
    """
