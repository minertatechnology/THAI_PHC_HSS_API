from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauth_clients"
            ADD COLUMN IF NOT EXISTS "allowlist_enabled" BOOLEAN NOT NULL DEFAULT FALSE;
        CREATE INDEX IF NOT EXISTS "idx_oauth_clients_allowlist_enabled" ON "oauth_clients" ("allowlist_enabled");

        CREATE TABLE IF NOT EXISTS "oauth_client_allows" (
            "id" UUID NOT NULL PRIMARY KEY,
            "client_id" UUID NOT NULL REFERENCES "oauth_clients" ("id") ON DELETE CASCADE,
            "user_id" UUID NOT NULL,
            "user_type" VARCHAR(50) NOT NULL,
            "citizen_id" VARCHAR(20),
            "full_name" VARCHAR(255),
            "note" VARCHAR(255),
            "created_by" UUID NOT NULL,
            "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            "updated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS "uq_oauth_client_allows_unique" ON "oauth_client_allows" ("client_id", "user_id", "user_type");
        CREATE INDEX IF NOT EXISTS "idx_oauth_client_allows_client" ON "oauth_client_allows" ("client_id");
        CREATE INDEX IF NOT EXISTS "idx_oauth_client_allows_user" ON "oauth_client_allows" ("user_id", "user_type");
        CREATE INDEX IF NOT EXISTS "idx_oauth_client_allows_citizen" ON "oauth_client_allows" ("citizen_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "oauth_client_allows";
        ALTER TABLE "oauth_clients" DROP COLUMN IF EXISTS "allowlist_enabled";
    """
