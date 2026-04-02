from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE \"officers\" ALTER COLUMN \"gender\" DROP NOT NULL;
        ALTER TABLE \"officers\" ALTER COLUMN \"birth_date\" DROP NOT NULL;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        UPDATE \"officers\"
        SET \"gender\" = 'other'
        WHERE \"gender\" IS NULL;

        UPDATE \"officers\"
        SET \"birth_date\" = DATE '1970-01-01'
        WHERE \"birth_date\" IS NULL;

        ALTER TABLE \"officers\" ALTER COLUMN \"gender\" SET NOT NULL;
        ALTER TABLE \"officers\" ALTER COLUMN \"birth_date\" SET NOT NULL;
    """
