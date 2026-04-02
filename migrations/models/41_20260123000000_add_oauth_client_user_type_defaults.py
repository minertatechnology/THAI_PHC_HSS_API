from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "oauth_client_user_type_defaults" (
            "id" UUID NOT NULL PRIMARY KEY,
            "client_id" UUID NOT NULL REFERENCES "oauth_clients" ("id") ON DELETE CASCADE,
            "allowed_user_types" JSONB,
            "created_by" UUID,
            "updated_by" UUID,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE ("client_id")
        );
        CREATE INDEX IF NOT EXISTS "idx_oauth_client_user_type_defaults_client" ON "oauth_client_user_type_defaults" ("client_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "oauth_client_user_type_defaults";
    """
