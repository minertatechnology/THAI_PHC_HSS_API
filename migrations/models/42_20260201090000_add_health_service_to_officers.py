from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "officers" ADD COLUMN IF NOT EXISTS "health_service_id" VARCHAR(255);
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_officers_health_service'
            ) THEN
                ALTER TABLE "officers"
                    ADD CONSTRAINT "fk_officers_health_service"
                    FOREIGN KEY ("health_service_id")
                    REFERENCES "health_services" ("health_service_code")
                    ON DELETE SET NULL;
            END IF;
        END $$;
        CREATE INDEX IF NOT EXISTS "idx_officers_health_service_id" ON "officers" ("health_service_id");
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "idx_officers_health_service_id";
        ALTER TABLE "officers" DROP CONSTRAINT IF EXISTS "fk_officers_health_service";
        ALTER TABLE "officers" DROP COLUMN IF EXISTS "health_service_id";
    """
