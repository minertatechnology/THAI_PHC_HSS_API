from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "osm_notifications" (
    "id" UUID NOT NULL PRIMARY KEY,
    "actor_id" UUID NOT NULL,
    "actor_name" VARCHAR(100) NOT NULL,
    "action_type" VARCHAR(20) NOT NULL,
    "target_type" VARCHAR(20) NOT NULL,
    "target_id" UUID NOT NULL,
    "target_name" VARCHAR(100) NOT NULL,
    "message" VARCHAR(300) NOT NULL,
    "province_code" VARCHAR(6),
    "district_code" VARCHAR(8),
    "subdistrict_code" VARCHAR(10),
    "health_area_id" VARCHAR(10),
    "region_code" VARCHAR(10),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_osm_notific_actor_i_2f20bd" ON "osm_notifications" ("actor_id");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_action__b40f4a" ON "osm_notifications" ("action_type");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_target__7ac021" ON "osm_notifications" ("target_type");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_target__860e89" ON "osm_notifications" ("target_id");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_provinc_7fa818" ON "osm_notifications" ("province_code");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_distric_46c70d" ON "osm_notifications" ("district_code");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_subdist_eef77c" ON "osm_notifications" ("subdistrict_code");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_health__a5f21a" ON "osm_notifications" ("health_area_id");
CREATE INDEX IF NOT EXISTS "idx_osm_notific_region__eb387a" ON "osm_notifications" ("region_code");
COMMENT ON TABLE "osm_notifications" IS 'Notification record created when OSM/Yuwa-OSM data is modified.';
        CREATE TABLE IF NOT EXISTS "osm_notification_reads" (
    "id" UUID NOT NULL PRIMARY KEY,
    "officer_id" UUID NOT NULL,
    "read_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "notification_id" UUID NOT NULL REFERENCES "osm_notifications" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_osm_notific_notific_dd5898" UNIQUE ("notification_id", "officer_id")
);
CREATE INDEX IF NOT EXISTS "idx_osm_notific_officer_5b9e81" ON "osm_notification_reads" ("officer_id");
COMMENT ON TABLE "osm_notification_reads" IS 'Tracks which officer has read which notification (fan-out on read).';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "osm_notifications";
        DROP TABLE IF EXISTS "osm_notification_reads";"""
