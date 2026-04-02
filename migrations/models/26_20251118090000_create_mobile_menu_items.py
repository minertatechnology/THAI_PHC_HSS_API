from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "mobile_menu_items" (
    "id" UUID NOT NULL PRIMARY KEY,
    "menu_key" VARCHAR(100) NOT NULL UNIQUE,
    "menu_name" VARCHAR(255) NOT NULL,
    "menu_description" TEXT,
    "icon_name" VARCHAR(255),
    "open_type" VARCHAR(50) NOT NULL DEFAULT 'webview',
    "webview_title" VARCHAR(255),
    "webview_url" VARCHAR(512),
    "redirect_url" VARCHAR(512),
    "deeplink_url" VARCHAR(512),
    "allowed_user_types" JSONB NOT NULL DEFAULT '[]'::jsonb,
    "platforms" JSONB NOT NULL DEFAULT '[]'::jsonb,
    "metadata" JSONB,
    "display_order" INT NOT NULL DEFAULT 0,
    "is_active" BOOL NOT NULL DEFAULT TRUE,
    "created_by" UUID,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_mobile_menu_items_name" ON "mobile_menu_items" ("menu_name");
CREATE INDEX IF NOT EXISTS "idx_mobile_menu_items_open_type" ON "mobile_menu_items" ("open_type");
CREATE INDEX IF NOT EXISTS "idx_mobile_menu_items_display_order" ON "mobile_menu_items" ("display_order");
CREATE INDEX IF NOT EXISTS "idx_mobile_menu_items_is_active" ON "mobile_menu_items" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_mobile_menu_items_created_by" ON "mobile_menu_items" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_mobile_menu_items_updated_by" ON "mobile_menu_items" ("updated_by");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "mobile_menu_items";"""
