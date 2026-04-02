from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
    CREATE TABLE "report_definitions" (
        "id" UUID NOT NULL PRIMARY KEY,
        "name" VARCHAR(100) NOT NULL UNIQUE,
        "label" VARCHAR(255) NOT NULL,
        "description" TEXT,
        "is_active" BOOL NOT NULL DEFAULT TRUE,
        "created_by" VARCHAR(255),
        "updated_by" VARCHAR(255),
        "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        "deleted_at" TIMESTAMPTZ
    );

    INSERT INTO "report_definitions" ("id", "name", "label", "description", "is_active", "created_by", "updated_by", "created_at", "updated_at") VALUES
        ('a95fa0f3-7cf0-4d47-9d5d-7d4ac2c04f67', 'standardByGender', 'รายงานมาตราฐาน อสม. จำแนกตามเพศ', 'รายงานมาตราฐาน อสม. จำแนกตามเพศ', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('f5d8128d-3f1a-4ad0-9bb5-2e6e3a0ed0fb', 'standardByAddress', 'รายงานตารางรายชื่อและที่อยู่ อสม. และสมาชิกครอบครัวทั้งหมด', 'รายงานตารางรายชื่อและที่อยู่ อสม. และสมาชิกครอบครัวทั้งหมด', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('2b91c268-8695-4d9a-9b84-9777084df14c', 'presidentList', 'รายงานแสดงรายชื่อประธาน อสม.', 'รายงานแสดงรายชื่อประธาน อสม.', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('ba6ff8d2-9d7f-4504-9f43-6f5dd1fb669f', 'resignedList', 'รายงานแสดงรายชื่อ อสม. ที่พ้นสภาพ', 'รายงานแสดงรายชื่อ อสม. ที่พ้นสภาพ', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('8f0c2c6c-394e-4c34-ba3d-f4d1cc0f2f2e', 'benefitClaimList', 'รายงานแสดงรายชื่อ อสม. ที่ร้องสิทธิรักษาป่วยการ 2,000 บาท', 'รายงานแสดงรายชื่อ อสม. ที่ร้องสิทธิรักษาป่วยการ 2,000 บาท', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('0b7ef0b3-9fcb-4b65-8dc5-1a5da2f8d63a', 'newByYearList', 'รายงานแสดงรายชื่อ อสม. ใหม่ ที่มีอายุการทำงานแบ่งตามปี', 'รายงานแสดงรายชื่อ อสม. ใหม่ ที่มีอายุการทำงานแบ่งตามปี', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('bfb94f2f-8483-47d8-97ef-5d66560fdf35', 'allAndDurationList', 'รายชื่อ อสม. ทุกคน และระยะเวลาการเป็นอสม.', 'รายชื่อ อสม. ทุกคน และระยะเวลาการเป็นอสม.', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('82ef0cb2-0c98-4ee3-8b98-7f90f5530a5a', 'averageAgeReport', 'รายงานแสดงอายุเฉลี่ยของ อสม.', 'รายงานแสดงอายุเฉลี่ยของ อสม.', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('4cff4b7b-6ef3-4156-8b18-447c25827d37', 'qualifiedForBenefitList', 'รายชื่อ อสม. ที่มีสิทธิรับค่าป่วยการ', 'รายชื่อ อสม. ที่มีสิทธิรับค่าป่วยการ', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('f0aa5a8c-2005-4cde-b5f4-ff1810c6a314', 'standardConfirmedByArea', 'รายงานตารางรายชื่อ อสม. ที่ได้รับเข็ม จำแนกตามตำบล และอำเภอ', 'รายงานตารางรายชื่อ อสม. ที่ได้รับเข็ม จำแนกตามตำบล และอำเภอ', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('f998948b-8105-4c88-84b0-460f5c6805b4', 'standardByAreaNeed', 'รายงานตารางรายชื่อ อสม. ตามความชำนาญ จำแนกตามตำบล และอำเภอ', 'รายงานตารางรายชื่อ อสม. ตามความชำนาญ จำแนกตามตำบล และอำเภอ', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('99811458-6e3f-4c1a-8dea-448f3c7c6bfa', 'positionsByVillage', 'ข้อมูล อสม. ที่ดำรงตำแหน่งอื่น เพื่อยืนยันการรับเงินค่าป่วยการ อสม', 'ข้อมูล อสม. ที่ดำรงตำแหน่งอื่น เพื่อยืนยันการรับเงินค่าป่วยการ อสม', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('4826f4c0-ec51-4794-9494-c620a0c2e60f', 'presidentByLevel', 'รายงาน รายชื่อ อสม. ที่มีตำแหน่งประธานชมรมอสม. ในระดับต่างๆ ตามพื้นที่แต่ละจังหวัด', 'รายงาน รายชื่อ อสม. ที่มีตำแหน่งประธานชมรมอสม. ในระดับต่างๆ ตามพื้นที่แต่ละจังหวัด', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('778b65c7-5509-4a06-96f4-9e2d4c1d9409', 'trainingByArea', 'รายงานจำนวน อสม. ที่ได้รับการอบรม อสม.ช. ในแต่ละพื้นที่', 'รายงานจำนวน อสม. ที่ได้รับการอบรม อสม.ช. ในแต่ละพื้นที่', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('1d2814af-ba67-4d0a-b975-67f3b997d4a5', 'resignedReport', 'รายงาน รายชื่อ อสม. พ้นสภาพ', 'รายงาน รายชื่อ อสม. พ้นสภาพ', TRUE, 'system', 'system', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
    DROP TABLE IF EXISTS "report_definitions";
    """
