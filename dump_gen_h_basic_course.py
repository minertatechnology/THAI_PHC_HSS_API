"""
Import CSV รายชื่อ+เกียรติบัตร หลูกสูตรพื้นฐาน → gen_h_user (ฐานตัวกลาง)

Logic:
  1. อ่าน CSV
  2. เช็ครายการที่มีอยู่แล้วใน gen_h_user (match โดย gen_h_code / citizen_id)
  3. Parse ชื่อ-นามสกุล → prefix, first_name, last_name
  4. Generate gen_h_code สำหรับรายการใหม่ (ใช้ atomic counter)
  5. Bulk insert เข้า gen_h_user
  6. certificate_link เก็บใน attachments JSON field

Usage:
    python dump_gen_h_basic_course.py <csv_file_path>
    python dump_gen_h_basic_course.py "C:\\Users\\Acer\\Downloads\\รายชื่อ+เกียรติบัตร หลูกสูตรพื้นฐาน - ชีต1.csv"
    python dump_gen_h_basic_course.py --dry-run <csv_file_path>   # แสดงสถิติโดยไม่ insert
"""

import asyncio
import csv
import io
import os
import sys
import time
from datetime import datetime

# Fix Windows console encoding for Thai & emoji
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ให้สามารถ import จาก project root
sys.path.insert(0, os.path.dirname(__file__))

# ── Constants ────────────────────────────────────────────────────────────────

PREFIXES = [
    "นางสาว", "นาง", "นาย", "น.ส.", "น.ช.",
    "ด.ญ.", "ด.ช.",
    "เด็กหญิง", "เด็กชาย",
]

GENDER_MAP = {
    "นาย": "male", "ด.ช.": "male", "เด็กชาย": "male",
    "นาง": "female", "นางสาว": "female", "น.ส.": "female",
    "ด.ญ.": "female", "เด็กหญิง": "female",
}

# CSV column names
COL_SEQ = "ลำดับ"
COL_NAME = "ชื่อ-นามสกุล"
COL_CODE = "รหัสประจำตัว"
COL_SCHOOL = "ชื่อโรงเรียน/องค์กร"
COL_PROVINCE = "จังหวัด"
COL_CERT_LINK = "Link ประกาศนีบัตร"


# ── Helpers ──────────────────────────────────────────────────────────────────

def clean_header(header: str) -> str:
    """ลบ BOM, quotes, whitespace ออกจาก header"""
    return header.strip().strip('"').strip("﻿")


def parse_thai_name(full_name: str) -> tuple:
    """Parse Thai full name → (prefix, first_name, last_name)"""
    name = full_name.strip()
    if not name:
        return None, "", ""

    for prefix in PREFIXES:
        if name.startswith(prefix):
            rest = name[len(prefix):].strip()
            parts = rest.split()
            if len(parts) >= 2:
                return prefix, parts[0], " ".join(parts[1:])
            elif len(parts) == 1:
                return prefix, parts[0], ""
            else:
                return prefix, "", ""

    # No known prefix → split by space
    parts = name.split()
    if len(parts) >= 2:
        return None, parts[0], " ".join(parts[1:])
    return None, name, ""


def load_dotenv(env_path: str):
    """Load .env file manually (ไม่ต้องการ python-dotenv library)"""
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                os.environ.setdefault(key, value)


# ── Main ─────────────────────────────────────────────────────────────────────

async def import_csv(csv_path: str, dry_run: bool = False):
    print("=" * 60)
    print("📋 Import CSV → gen_h_user (หลูกสูตรพื้นฐาน)")
    print("=" * 60)
    print(f"📁 CSV: {csv_path}")
    print(f"🔧 Mode: {'DRY RUN (ไม่ insert)' if dry_run else 'LIVE INSERT'}")
    print()

    # 1. Read CSV
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {clean_header(k): v for k, v in row.items()}
            rows.append(cleaned)

    print(f"📊 ข้อมูลใน CSV: {len(rows):,} รายการ")

    if not rows:
        print("⚠️ CSV ว่าง ไม่มีข้อมูลนำเข้า")
        return

    # ── DB connection (skip in dry-run) ──────────────────────────────────────
    existing_codes = set()
    existing_cids = set()

    if not dry_run:
        from app.configs.config import settings
        from app.models.gen_h_model import GenHUser
        from tortoise import Tortoise, connections
        from urllib.parse import urlparse
        import os as _os

        # Build minimal config — เฉพาะ gen_h_model ไม่ต้องโหลด aerich
        db_url = _os.getenv("DATABASE_URL", settings.POSTGRES_DATABASE_URL)
        parsed = urlparse(db_url)
        db_name = (parsed.path or "/").lstrip("/")
        scheme = (parsed.scheme or "postgres").lower()

        db_config = {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg" if scheme != "sqlite" else "tortoise.backends.sqlite",
                    "credentials": {
                        "host": parsed.hostname or "localhost",
                        "port": parsed.port or 5432,
                        "user": parsed.username,
                        "password": parsed.password,
                        "database": db_name,
                    } if scheme != "sqlite" else {"file_path": db_name},
                },
            },
            "apps": {
                "models": {
                    "models": ["app.models.gen_h_model"],
                    "default_connection": "default",
                },
            },
        }
        await Tortoise.init(config=db_config)

        print("🔍 เช็คข้อมูลที่มีอยู่ในฐาน...")

        # Existing gen_h_codes
        all_users = await GenHUser.all().values_list("gen_h_code", "citizen_id")
        existing_codes = {u[0] for u in all_users if u[0]}
        existing_cids = {u[1] for u in all_users if u[1]}
        print(f"   ✅ gen_h_user ทั้งหมด: {len(all_users):,} รายการ")
    else:
        print("🔍 DRY RUN — ข้ามการเชื่อมต่อฐานข้อมูล")

    # ── Parse & classify ───────────────────────────────────────────────────
    new_records = []
    stats = {
        "skipped_code_exists": 0,
        "skipped_cid_exists": 0,
        "skipped_empty_name": 0,
        "skipped_no_code": 0,
        "new_records": 0,
    }

    for i, row in enumerate(rows):
        code = row.get(COL_CODE, "").strip()
        full_name = row.get(COL_NAME, "").strip()
        school = row.get(COL_SCHOOL, "").strip() or None
        province = row.get(COL_PROVINCE, "").strip() or None
        cert_link = row.get(COL_CERT_LINK, "").strip() or None

        # Skip if no code at all
        if not code:
            stats["skipped_no_code"] += 1
            continue

        # Skip if gen_h_code already exists
        if code in existing_codes:
            stats["skipped_code_exists"] += 1
            continue

        # Skip if citizen_id match (for 13-digit codes)
        if len(code) == 13 and code in existing_cids:
            stats["skipped_cid_exists"] += 1
            continue

        # Parse name
        prefix, first_name, last_name = parse_thai_name(full_name)

        if not first_name:
            stats["skipped_empty_name"] += 1
            continue

        gender = GENDER_MAP.get(prefix)

        # Build attachments JSON
        attachments = None
        if cert_link:
            attachments = {
                "source": "basic_course_csv_import",
                "certificate_link": cert_link,
                "csv_member_code": code,
            }

        new_records.append({
            "csv_code": code,
            "prefix": prefix,
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "school": school,
            "organization": school,
            "province_name": province,
            "citizen_id": code if len(code) == 13 else None,
            "attachments": attachments,
            "source_type": "migration",
            "created_by": "csv_import_basic_course",
            "is_active": True,
            "is_first_login": True,
            "password_attempts": 0,
            # password_hash จะถูกตั้งหลัง generate gen_h_code (รหัสผ่าน = gen_h_code)
        })
        stats["new_records"] += 1

    # ── Print stats ─────────────────────────────────────────────────────────
    print()
    print("📈 สถิติการกรอง:")
    print(f"   ⏭️  มี gen_h_code อยู่แล้ว: {stats['skipped_code_exists']:,} รายการ")
    print(f"   ⏭️  มี citizen_id อยู่แล้ว: {stats['skipped_cid_exists']:,} รายการ")
    print(f"   ⏭️  รหัสว่าง/ไม่มีรหัส:    {stats['skipped_no_code']:,} รายการ")
    print(f"   ⏭️  ชื่อไม่สมบูรณ์:        {stats['skipped_empty_name']:,} รายการ")
    print(f"   📥 จะนำเข้าใหม่:          {stats['new_records']:,} รายการ")
    print()

    if not new_records:
        print("🎉 ข้อมูลใน CSV มีอยู่ในฐานหมดแล้ว ไม่ต้องนำเข้าเพิ่ม")
        if not dry_run:
            await Tortoise.close_connections()
        return

    if dry_run:
        print("✅ DRY RUN เสร็จ — ไม่มีการเปลี่ยนแปลงข้อมูล")
        return

    # ── Generate gen_h_codes ───────────────────────────────────────────────
    print("🔢 สร้าง gen_h_code สำหรับรายการใหม่...")
    thai_year = datetime.now().year + 543
    year2 = str(thai_year)[-2:]  # e.g. "69"
    counter_key = f"GH{year2}"

    db = connections.get("default")

    # จำนวนที่ต้อง generate
    need_code_count = len(new_records)

    # Atomic batch increment
    result = await db.execute_query_dict(
        f"""
        INSERT INTO osm_code_counters (prefix, last_number, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (prefix) DO UPDATE
            SET last_number = osm_code_counters.last_number + $2,
                updated_at = NOW()
        RETURNING last_number
        """,
        [counter_key, need_code_count],
    )
    end_number = result[0]["last_number"]
    start_number = end_number - need_code_count + 1

    import bcrypt as _bcrypt

    print(f"   🔐 Hash รหัสผ่าน (bcrypt rounds=4 สำหรับ migration)...")
    hash_start = time.time()
    salt = _bcrypt.gensalt(rounds=4)  # ต่ำสำหรับ migration — จะเปลี่ยนตอน first login
    for idx, rec in enumerate(new_records):
        gen_h_code = f"{year2}{start_number + idx:06d}"
        rec["gen_h_code"] = gen_h_code
        rec["password_hash"] = _bcrypt.hashpw(gen_h_code.encode(), salt).decode()
        if (idx + 1) % 2000 == 0:
            print(f"      hashed {idx + 1:,}/{need_code_count:,} ({time.time() - hash_start:.1f}s)")
    print(f"   ✅ Hash เสร็จ ({time.time() - hash_start:.1f}s)")
    print(f"   ✅ สร้าง {need_code_count:,} codes: {year2}{start_number:06d} – {year2}{end_number:06d}")
    print(f"   🔑 รหัสผ่าน = gen_h_code (ต้องเปลี่ยนตอน login ครั้งแรก)")

    # ── Bulk insert ─────────────────────────────────────────────────────────
    print("🚀 เริ่มนำเข้าข้อมูล...")
    start_time = time.time()

    batch_size = 500
    created_count = 0
    error_count = 0

    for i in range(0, len(new_records), batch_size):
        batch = new_records[i : i + batch_size]

        # ลบ csv_code ออก (ไม่ใช่ field ใน model)
        clean_batch = []
        for rec in batch:
            clean_rec = {k: v for k, v in rec.items() if k != "csv_code"}
            clean_batch.append(GenHUser(**clean_rec))

        try:
            await GenHUser.bulk_create(clean_batch)
            created_count += len(clean_batch)
        except Exception as e:
            # Fallback: insert ทีละรายการ สำหรับ handle duplicate
            print(f"   ⚠️ Batch error (row {i}): {e}")
            for rec in batch:
                clean_rec = {k: v for k, v in rec.items() if k != "csv_code"}
                try:
                    await GenHUser.create(**clean_rec)
                    created_count += 1
                except Exception as e2:
                    error_count += 1
                    if error_count <= 5:
                        print(f"      ❌ {clean_rec['gen_h_code']}: {e2}")

        print(f"   Batch {i // batch_size + 1}: +{len(batch):,} ({created_count:,}/{len(new_records):,})")

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print(f"✅ เสร็จสิ้น!")
    print(f"   นำเข้าสำเร็จ: {created_count:,} รายการ")
    if error_count:
        print(f"   ผิดพลาด:       {error_count:,} รายการ")
    print(f"   ใช้เวลา:       {elapsed:.2f} วินาที")

    # Final count
    total = await GenHUser.all().count()
    print(f"   รวม gen_h_user ในฐานตอนนี้: {total:,} รายการ")
    print("=" * 60)

    await Tortoise.close_connections()


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if len(args) < 1:
        print("Usage:")
        print("  python dump_gen_h_basic_course.py <csv_file_path>")
        print('  python dump_gen_h_basic_course.py "C:\\Users\\Acer\\Downloads\\file.csv"')
        print("  python dump_gen_h_basic_course.py --dry-run <csv_file_path>   # ดูสถิติก่อน")
        sys.exit(1)

    csv_file = args[0]
    if not os.path.exists(csv_file):
        print(f"❌ ไม่พบไฟล์: {csv_file}")
        sys.exit(1)

    # Load .env before importing app modules
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    asyncio.run(import_csv(csv_file, dry_run=dry_run))
