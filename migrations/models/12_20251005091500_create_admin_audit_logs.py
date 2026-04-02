from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE IF NOT EXISTS "admin_audit_logs" (
        "id" UUID NOT NULL PRIMARY KEY,
        "user_id" UUID,
        "action_type" VARCHAR(255) NOT NULL,
        "target_type" VARCHAR(255) NOT NULL,
        "description" VARCHAR(500),
        "old_data" JSONB,
        "new_data" JSONB,
        "ip_address" VARCHAR(100),
        "user_agent" VARCHAR(500),
        "success" BOOL NOT NULL DEFAULT True,
        "error_message" VARCHAR(1000),
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS "idx_admin_audi_user_id_5b8e3c" ON "admin_audit_logs" ("user_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP TABLE IF EXISTS "admin_audit_logs";
    """
