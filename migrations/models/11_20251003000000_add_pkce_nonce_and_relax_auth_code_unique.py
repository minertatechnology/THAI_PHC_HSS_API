from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    -- Relax unique constraint on oauth_authorization_codes.client_id by recreating index
    DROP INDEX IF EXISTS "idx_oauth_autho_client__6350fa";
    -- Drop implicit unique constraint created by column UNIQUE declaration (name may vary by DB)
    ALTER TABLE "oauth_authorization_codes" DROP CONSTRAINT IF EXISTS oauth_authorization_codes_client_id_key;
    -- Add PKCE and nonce columns
    ALTER TABLE "oauth_authorization_codes" ADD COLUMN IF NOT EXISTS "code_challenge" VARCHAR(255);
    ALTER TABLE "oauth_authorization_codes" ADD COLUMN IF NOT EXISTS "code_challenge_method" VARCHAR(10);
    ALTER TABLE "oauth_authorization_codes" ADD COLUMN IF NOT EXISTS "nonce" VARCHAR(255);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    ALTER TABLE "oauth_authorization_codes" DROP COLUMN IF EXISTS "code_challenge";
    ALTER TABLE "oauth_authorization_codes" DROP COLUMN IF EXISTS "code_challenge_method";
    ALTER TABLE "oauth_authorization_codes" DROP COLUMN IF EXISTS "nonce";
    """
