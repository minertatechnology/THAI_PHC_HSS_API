from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return "ALTER TABLE \"officers\" ADD \"password_attempts\" INT NOT NULL DEFAULT 0;"


async def downgrade(db: BaseDBAsyncClient) -> str:
    return "ALTER TABLE \"officers\" DROP COLUMN \"password_attempts\";"
