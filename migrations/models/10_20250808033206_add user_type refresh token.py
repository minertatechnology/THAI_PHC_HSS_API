from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "oauth_authorization_codes" ADD "user_type" VARCHAR(255) NOT NULL;
        ALTER TABLE "refresh_tokens" ADD "user_type" VARCHAR(255);
        CREATE INDEX IF NOT EXISTS "idx_oauth_autho_user_ty_e7b26b" ON "oauth_authorization_codes" ("user_type");
        CREATE INDEX IF NOT EXISTS "idx_refresh_tok_user_ty_85a860" ON "refresh_tokens" ("user_type");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_oauth_autho_user_ty_e7b26b";
        DROP INDEX IF EXISTS "idx_refresh_tok_user_ty_85a860";
        ALTER TABLE "refresh_tokens" DROP COLUMN "user_type";
        ALTER TABLE "oauth_authorization_codes" DROP COLUMN "user_type";"""
