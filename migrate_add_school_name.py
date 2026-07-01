"""
Migration: เพิ่ม school_name column ใน gen_h_user, people_user, yuwa_osm_user tables
แล้ว update school_name จาก school code (ใช้ school table จาก yuwa_osm_mobile_db)
Run: python migrate_add_school_name.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.configs.config import settings
import asyncpg

# Database URLs
AUTH_DB_URL = settings.POSTGRES_DATABASE_URL  # THAI_PHC_HSS_API DB
MOBILE_DB_URL = "postgresql://smart_osm_user:Q7mZ8pKa42@192.168.88.61:6432/yuwa_osm"

async def migrate():
    # 1. Connect to AUTH DB
    conn = await asyncpg.connect(AUTH_DB_URL, statement_cache_size=0)

    tables = ["gen_h_user", "people_user", "yuwa_osm_user"]

    # 2. Add school_name column if not exists
    for table in tables:
        result = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name=$1 AND column_name='school_name'",
            table
        )
        if result:
            print(f"[OK] school_name already exists in {table}")
        else:
            await conn.execute(f'ALTER TABLE "{table}" ADD COLUMN "school_name" VARCHAR(255)')
            print(f"[OK] Added school_name to {table}")

    # 3. Update school_name from schools table in MOBILE DB
    try:
        mobile_conn = await asyncpg.connect(MOBILE_DB_URL, statement_cache_size=0)

        # ดึง school_id -> school_na mapping จาก mobile DB
        school_rows = await mobile_conn.fetch("SELECT school_id, school_na FROM schools WHERE school_na IS NOT NULL")
        school_map = {str(row['school_id']): row['school_na'] for row in school_rows}
        await mobile_conn.close()

        if school_map:
            print(f"[INFO] Found {len(school_map)} schools in mobile DB")

            for table in tables:
                # ดึง rows ที่ school_name เป็น NULL แต่ school เป็นตัวเลข
                rows = await conn.fetch(
                    f'SELECT id, school FROM "{table}" WHERE school_name IS NULL AND school IS NOT NULL'
                )
                updated = 0
                for row in rows:
                    school_code = str(row['school']).strip()
                    if school_code.isdigit() and school_code in school_map:
                        await conn.execute(
                            f'UPDATE "{table}" SET school_name = $1 WHERE id = $2',
                            school_map[school_code], row['id']
                        )
                        updated += 1
                print(f"[OK] Updated {updated}/{len(rows)} rows in {table}")
        else:
            print("[WARN] No schools found in mobile DB")
    except Exception as e:
        print(f"[WARN] Could not connect to mobile DB: {e}")
        print("[INFO] school_name will be populated when users come online via auth service")

    await conn.close()
    print("[DONE] Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
