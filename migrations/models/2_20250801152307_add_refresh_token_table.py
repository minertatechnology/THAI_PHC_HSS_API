from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "refresh_tokens" (
    "id" UUID NOT NULL PRIMARY KEY,
    "token" VARCHAR(255) NOT NULL UNIQUE,
    "user_id" UUID NOT NULL,
    "client_id" VARCHAR(255) NOT NULL,
    "scopes" JSONB NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "is_revoked" BOOL NOT NULL DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_refresh_tok_token_369bea" ON "refresh_tokens" ("token");
CREATE INDEX IF NOT EXISTS "idx_refresh_tok_user_id_9ddaa8" ON "refresh_tokens" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_refresh_tok_client__bcd7b4" ON "refresh_tokens" ("client_id");
CREATE INDEX IF NOT EXISTS "idx_refresh_tok_is_revo_3170d0" ON "refresh_tokens" ("is_revoked");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "refresh_tokens";"""
