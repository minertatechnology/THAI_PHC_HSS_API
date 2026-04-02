from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_credentials" (
    "id" UUID NOT NULL PRIMARY KEY,
    "identifier_value" VARCHAR(50) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "user_type" VARCHAR(50) NOT NULL,
    "user_id" UUID NOT NULL,
    "is_legacy_password" BOOL NOT NULL DEFAULT False,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_user_creden_identif_3ee300" ON "user_credentials" ("identifier_value");
COMMENT ON TABLE "user_credentials" IS 'The UserCredential model';
CREATE TABLE IF NOT EXISTS "oauth_authorization_codes" (
    "id" UUID NOT NULL PRIMARY KEY,
    "code" VARCHAR(255) NOT NULL UNIQUE,
    "user_id" UUID NOT NULL,
    "client_id" VARCHAR(255) NOT NULL UNIQUE,
    "scopes" JSONB NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_oauth_autho_code_637531" ON "oauth_authorization_codes" ("code");
CREATE INDEX IF NOT EXISTS "idx_oauth_autho_user_id_34c267" ON "oauth_authorization_codes" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_oauth_autho_client__6350fa" ON "oauth_authorization_codes" ("client_id");
CREATE TABLE IF NOT EXISTS "oauth_clients" (
    "id" UUID NOT NULL PRIMARY KEY,
    "client_id" VARCHAR(255) NOT NULL UNIQUE,
    "client_secret" VARCHAR(255) NOT NULL,
    "client_name" VARCHAR(255) NOT NULL,
    "client_description" VARCHAR(255),
    "redirect_uri" TEXT NOT NULL,
    "scopes" JSONB NOT NULL,
    "grant_types" JSONB NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_oauth_clien_client__4a803d" ON "oauth_clients" ("client_id");
CREATE INDEX IF NOT EXISTS "idx_oauth_clien_is_acti_d76e10" ON "oauth_clients" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_oauth_clien_created_ed4055" ON "oauth_clients" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_oauth_clien_updated_965469" ON "oauth_clients" ("updated_by");
CREATE TABLE IF NOT EXISTS "oauth_consents" (
    "id" UUID NOT NULL PRIMARY KEY,
    "user_id" UUID NOT NULL,
    "client_id" VARCHAR(255) NOT NULL,
    "scopes" JSONB NOT NULL,
    "accepted_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "uid_oauth_conse_user_id_5c6347" UNIQUE ("user_id", "client_id")
);
CREATE INDEX IF NOT EXISTS "idx_oauth_conse_user_id_59029e" ON "oauth_consents" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_oauth_conse_client__55f453" ON "oauth_consents" ("client_id");
CREATE TABLE IF NOT EXISTS "regions" (
    "code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "region_name_th" VARCHAR(255) NOT NULL,
    "region_name_en" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "areas" (
    "code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "area_name_th" VARCHAR(255) NOT NULL,
    "area_name_en" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "region_id" VARCHAR(255) REFERENCES "regions" ("code") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "health_areas" (
    "code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "health_area_name_th" VARCHAR(255) NOT NULL,
    "health_area_name_en" VARCHAR(255) NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_health_area_created_39469f" ON "health_areas" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_health_area_updated_3c2893" ON "health_areas" ("updated_by");
CREATE TABLE IF NOT EXISTS "provinces" (
    "province_code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "province_name_th" VARCHAR(255) NOT NULL,
    "province_name_en" VARCHAR(255),
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "area_id" VARCHAR(255) REFERENCES "areas" ("code") ON DELETE CASCADE,
    "health_area_id" VARCHAR(255) REFERENCES "health_areas" ("code") ON DELETE CASCADE,
    "region_id" VARCHAR(255) REFERENCES "regions" ("code") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "districts" (
    "district_code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "district_name_th" VARCHAR(255) NOT NULL,
    "district_name_en" VARCHAR(255),
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "province_id" VARCHAR(255) NOT NULL REFERENCES "provinces" ("province_code") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "subdistricts" (
    "subdistrict_code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "subdistrict_name_th" VARCHAR(255) NOT NULL,
    "subdistrict_name_en" VARCHAR(255),
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "postal_code" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "district_id" VARCHAR(255) NOT NULL REFERENCES "districts" ("district_code") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "health_service_types" (
    "id" UUID NOT NULL PRIMARY KEY,
    "health_service_type_name_th" VARCHAR(255) NOT NULL,
    "health_service_type_name_en" VARCHAR(255),
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_health_serv_created_36ff4a" ON "health_service_types" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_health_serv_updated_5a6295" ON "health_service_types" ("updated_by");
CREATE TABLE IF NOT EXISTS "health_services" (
    "health_service_code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "health_service_name_th" VARCHAR(255) NOT NULL,
    "health_service_name_en" VARCHAR(255),
    "legacy_5digit_code" VARCHAR(255),
    "legacy_9digit_code" VARCHAR(255),
    "village_no" VARCHAR(255),
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "district_id" VARCHAR(255) REFERENCES "districts" ("district_code") ON DELETE CASCADE,
    "health_service_type_id" UUID NOT NULL REFERENCES "health_service_types" ("id") ON DELETE CASCADE,
    "province_id" VARCHAR(255) REFERENCES "provinces" ("province_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_health_serv_created_f56b03" ON "health_services" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_health_serv_updated_3442f7" ON "health_services" ("updated_by");
CREATE TABLE IF NOT EXISTS "award_categories" (
    "id" UUID NOT NULL PRIMARY KEY,
    "award_category_name" VARCHAR(255) NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_award_categ_award_c_b5fe34" ON "award_categories" ("award_category_name");
CREATE INDEX IF NOT EXISTS "idx_award_categ_created_42e5e4" ON "award_categories" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_award_categ_updated_09b2c4" ON "award_categories" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_award_categ_created_dc8951" ON "award_categories" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_award_categ_updated_6c0e4e" ON "award_categories" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_award_categ_deleted_e92902" ON "award_categories" ("deleted_at");
CREATE TABLE IF NOT EXISTS "award_levels" (
    "id" UUID NOT NULL PRIMARY KEY,
    "award_level_name" VARCHAR(255) NOT NULL,
    "award_level" VARCHAR(11) NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_award_level_award_l_bebabd" ON "award_levels" ("award_level_name");
CREATE INDEX IF NOT EXISTS "idx_award_level_award_l_d04194" ON "award_levels" ("award_level");
CREATE INDEX IF NOT EXISTS "idx_award_level_created_60d05b" ON "award_levels" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_award_level_updated_54401f" ON "award_levels" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_award_level_created_fae733" ON "award_levels" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_award_level_updated_62e0fe" ON "award_levels" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_award_level_deleted_58770c" ON "award_levels" ("deleted_at");
COMMENT ON COLUMN "award_levels"."award_level" IS 'VILLAGE: village\nSUBDISTRICT: subdistrict\nDISTRICT: district\nPROVINCE: province\nAREA: area\nREGION: region\nCOUNTRY: country';
CREATE TABLE IF NOT EXISTS "pins" (
    "id" UUID NOT NULL PRIMARY KEY,
    "pin_name_th" VARCHAR(255) NOT NULL,
    "pin_name_en" VARCHAR(255),
    "legacy_id" INT,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_pins_pin_nam_cf52fc" ON "pins" ("pin_name_th");
CREATE INDEX IF NOT EXISTS "idx_pins_created_2cde4f" ON "pins" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_pins_updated_eff4f8" ON "pins" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_pins_created_7d2c9a" ON "pins" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_pins_updated_c5a0ee" ON "pins" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_pins_deleted_53ee10" ON "pins" ("deleted_at");
CREATE TABLE IF NOT EXISTS "training_categories" (
    "id" UUID NOT NULL PRIMARY KEY,
    "training_category_name_th" VARCHAR(255) NOT NULL,
    "training_category_name_en" VARCHAR(255),
    "legacy_id" INT,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_training_ca_trainin_d4bc2e" ON "training_categories" ("training_category_name_th");
CREATE INDEX IF NOT EXISTS "idx_training_ca_created_427693" ON "training_categories" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_training_ca_updated_e3712e" ON "training_categories" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_training_ca_created_3a1446" ON "training_categories" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_training_ca_updated_3c4917" ON "training_categories" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_training_ca_deleted_912a10" ON "training_categories" ("deleted_at");
CREATE TABLE IF NOT EXISTS "trainings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "training_name_th" VARCHAR(255) NOT NULL,
    "training_name_en" VARCHAR(255),
    "legacy_id" INT,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "training_category_id" UUID NOT NULL REFERENCES "training_categories" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_trainings_trainin_70ca77" ON "trainings" ("training_name_th");
CREATE INDEX IF NOT EXISTS "idx_trainings_created_cd36a2" ON "trainings" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_trainings_updated_1ae947" ON "trainings" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_trainings_created_262d2e" ON "trainings" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_trainings_updated_fd48c9" ON "trainings" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_trainings_deleted_0bc21b" ON "trainings" ("deleted_at");
CREATE INDEX IF NOT EXISTS "idx_trainings_trainin_4a2d4b" ON "trainings" ("training_category_id");
CREATE TABLE IF NOT EXISTS "banks" (
    "id" UUID NOT NULL PRIMARY KEY,
    "bank_name_th" VARCHAR(255) NOT NULL,
    "bank_name_en" VARCHAR(255) NOT NULL,
    "bank_code" VARCHAR(3),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "educations" (
    "id" UUID NOT NULL PRIMARY KEY,
    "education_name_th" VARCHAR(255) NOT NULL,
    "education_name_en" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "occupations" (
    "id" UUID NOT NULL PRIMARY KEY,
    "occupation_name_th" VARCHAR(255) NOT NULL,
    "occupation_name_en" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "prefixes" (
    "id" UUID NOT NULL PRIMARY KEY,
    "prefix_name_th" VARCHAR(255) NOT NULL,
    "prefix_name_en" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "osm_profiles" (
    "id" UUID NOT NULL PRIMARY KEY,
    "osm_code" VARCHAR(50),
    "citizen_id" VARCHAR(13) NOT NULL UNIQUE,
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(100) NOT NULL,
    "gender" VARCHAR(6) NOT NULL DEFAULT 'other',
    "birth_date" DATE,
    "email" VARCHAR(255),
    "phone" VARCHAR(50),
    "new_registration_allowance_status" VARCHAR(30) NOT NULL DEFAULT 'rejected',
    "is_allowance_supported" BOOL NOT NULL DEFAULT False,
    "allowance_year" INT,
    "allowance_months" INT,
    "non_formal_education_level" VARCHAR(16) NOT NULL DEFAULT 'not_study',
    "marital_status" VARCHAR(8) NOT NULL DEFAULT 'single',
    "number_of_children" INT NOT NULL DEFAULT 0,
    "blood_type" VARCHAR(7) NOT NULL DEFAULT 'other',
    "volunteer_status" VARCHAR(21) NOT NULL DEFAULT 'not_interested',
    "bank_account_number" VARCHAR(50),
    "is_smartphone_owner" BOOL NOT NULL DEFAULT False,
    "address_number" VARCHAR(100) NOT NULL,
    "village_no" VARCHAR(10),
    "village_code" VARCHAR(10),
    "alley" VARCHAR(255),
    "street" VARCHAR(255),
    "postal_code" VARCHAR(10),
    "is_active" BOOL NOT NULL DEFAULT False,
    "osm_year" INT,
    "approval_date" DATE,
    "approval_by" VARCHAR(255),
    "approval_status" VARCHAR(8) NOT NULL DEFAULT 'pending',
    "retirement_date" DATE,
    "retirement_reason" VARCHAR(36),
    "is_legacy_data" BOOL NOT NULL DEFAULT False,
    "created_by" VARCHAR(255) NOT NULL,
    "updated_by" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "bank_id" UUID REFERENCES "banks" ("id") ON DELETE CASCADE,
    "district_id" VARCHAR(255) REFERENCES "districts" ("district_code") ON DELETE CASCADE,
    "education_id" UUID NOT NULL REFERENCES "educations" ("id") ON DELETE CASCADE,
    "health_service_id" VARCHAR(255) REFERENCES "health_services" ("health_service_code") ON DELETE CASCADE,
    "occupation_id" UUID NOT NULL REFERENCES "occupations" ("id") ON DELETE CASCADE,
    "prefix_id" UUID NOT NULL REFERENCES "prefixes" ("id") ON DELETE CASCADE,
    "province_id" VARCHAR(255) REFERENCES "provinces" ("province_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_profile_osm_cod_4ba303" ON "osm_profiles" ("osm_code");
CREATE INDEX IF NOT EXISTS "idx_osm_profile_citizen_877613" ON "osm_profiles" ("citizen_id");
CREATE INDEX IF NOT EXISTS "idx_osm_profile_birth_d_2fcd1a" ON "osm_profiles" ("birth_date");
CREATE INDEX IF NOT EXISTS "idx_osm_profile_email_4dc547" ON "osm_profiles" ("email");
CREATE INDEX IF NOT EXISTS "idx_osm_profile_created_32171d" ON "osm_profiles" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_profile_updated_956c98" ON "osm_profiles" ("updated_by");
COMMENT ON COLUMN "osm_profiles"."gender" IS 'MALE: male\nFEMALE: female\nOTHER: other';
COMMENT ON COLUMN "osm_profiles"."new_registration_allowance_status" IS 'ACCEPTED: accepted\nACCEPTED_WITH_INCOMPLETE_PROOF: accepted_with_incomplete_proof\nNOT_VERIFIED_IDENTITY: not_verified_identity\nNEW_OSM_2553: new_osm_2553\nREJECTED: rejected\nPENDING: pending';
COMMENT ON COLUMN "osm_profiles"."non_formal_education_level" IS 'NOT_STUDY: not_study\nPRIMARY: primary\nJUNIOR_HIGH: junior_high\nSENIOR_HIGH: senior_high\nVOCATIONAL: vocational\nHIGHER_EDUCATION: higher_education';
COMMENT ON COLUMN "osm_profiles"."marital_status" IS 'SINGLE: single\nMARRIED: married\nDIVORCED: divorced\nWIDOWED: widowed\nOTHER: other';
COMMENT ON COLUMN "osm_profiles"."blood_type" IS 'A: A\nB: B\nAB: AB\nO: O\nOTHER: other\nUNKNOWN: unknown';
COMMENT ON COLUMN "osm_profiles"."volunteer_status" IS 'ALREADY_VOLUNTEER: already_volunteer\nWANTS_TO_BE_VOLUNTEER: wants_to_be_volunteer\nNOT_INTERESTED: not_interested';
COMMENT ON COLUMN "osm_profiles"."approval_status" IS 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected';
COMMENT ON COLUMN "osm_profiles"."retirement_reason" IS 'DIED: died\nRESIGNED: resigned\nMOVED_OR_ABSENT: moved_or_absent\nSICK_OR_DISABLED: sick_or_disabled\nNEVER_PARTICIPATED_IN_OSM_ACTIVITIES: never_participated_in_osm_activities\nCOMMUNITY_REQUESTS_REMOVAL: community_requests_removal\nBEHAVIOR_DAMAGING_REPUTATION: behavior_damaging_reputation';
CREATE TABLE IF NOT EXISTS "osm_outstandings" (
    "id" UUID NOT NULL PRIMARY KEY,
    "award_year" INT NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "award_level_id" UUID NOT NULL REFERENCES "award_levels" ("id") ON DELETE CASCADE,
    "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_outstan_created_53b484" ON "osm_outstandings" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_outstan_updated_fce7ea" ON "osm_outstandings" ("updated_by");
CREATE TABLE IF NOT EXISTS "osm_pins" (
    "id" UUID NOT NULL PRIMARY KEY,
    "received_pin_year" INT NOT NULL,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE,
    "pin_id" UUID NOT NULL REFERENCES "pins" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_pins_created_678021" ON "osm_pins" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_pins_updated_7853b4" ON "osm_pins" ("updated_by");
CREATE TABLE IF NOT EXISTS "leadership_positions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "position_name_th" VARCHAR(255) NOT NULL,
    "position_name_en" VARCHAR(255),
    "position_level" VARCHAR(11) NOT NULL,
    "legacy_id" INT,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_leadership__positio_6e2008" ON "leadership_positions" ("position_name_th");
CREATE INDEX IF NOT EXISTS "idx_leadership__positio_e70b14" ON "leadership_positions" ("position_level");
CREATE INDEX IF NOT EXISTS "idx_leadership__created_eb3f36" ON "leadership_positions" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_leadership__updated_ee769d" ON "leadership_positions" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_leadership__created_07ba72" ON "leadership_positions" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_leadership__updated_c15a07" ON "leadership_positions" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_leadership__deleted_6420f1" ON "leadership_positions" ("deleted_at");
COMMENT ON COLUMN "leadership_positions"."position_level" IS 'VILLAGE: village\nSUBDISTRICT: subdistrict\nDISTRICT: district\nPROVINCE: province\nAREA: area\nREGION: region\nCOUNTRY: country';
CREATE TABLE IF NOT EXISTS "osm_leadership_positions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "leadership_position_id" UUID NOT NULL REFERENCES "leadership_positions" ("id") ON DELETE CASCADE,
    "osm_profile_id" UUID NOT NULL REFERENCES "osm_profiles" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_osm_leaders_created_145fa6" ON "osm_leadership_positions" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_osm_leaders_updated_f4f965" ON "osm_leadership_positions" ("updated_by");
CREATE TABLE IF NOT EXISTS "municipality_types" (
    "code" VARCHAR(255) NOT NULL PRIMARY KEY,
    "municipality_type_name_th" VARCHAR(255) NOT NULL,
    "municipality_type_name_en" VARCHAR(255),
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_municipalit_created_54b4e5" ON "municipality_types" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_municipalit_updated_65683b" ON "municipality_types" ("updated_by");
CREATE TABLE IF NOT EXISTS "municipalities" (
    "id" UUID NOT NULL PRIMARY KEY,
    "municipality_name_th" VARCHAR(255) NOT NULL,
    "municipality_name_en" VARCHAR(255),
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "district_id" VARCHAR(255) REFERENCES "districts" ("district_code") ON DELETE CASCADE,
    "municipality_type_id" VARCHAR(255) NOT NULL REFERENCES "municipality_types" ("code") ON DELETE CASCADE,
    "province_id" VARCHAR(255) REFERENCES "provinces" ("province_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_municipalit_created_e1ae96" ON "municipalities" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_municipalit_updated_af6cfe" ON "municipalities" ("updated_by");
CREATE TABLE IF NOT EXISTS "positions" (
    "id" UUID NOT NULL PRIMARY KEY,
    "position_name_th" VARCHAR(255) NOT NULL,
    "position_name_en" VARCHAR(255),
    "position_code" VARCHAR(255) NOT NULL UNIQUE,
    "created_by" UUID NOT NULL,
    "updated_by" UUID,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_positions_positio_273996" ON "positions" ("position_name_th");
CREATE INDEX IF NOT EXISTS "idx_positions_positio_3b6084" ON "positions" ("position_code");
CREATE INDEX IF NOT EXISTS "idx_positions_created_ca0202" ON "positions" ("created_by");
CREATE INDEX IF NOT EXISTS "idx_positions_updated_3401f1" ON "positions" ("updated_by");
CREATE INDEX IF NOT EXISTS "idx_positions_created_4e1a0e" ON "positions" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_positions_updated_86054e" ON "positions" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_positions_deleted_65e7f9" ON "positions" ("deleted_at");
CREATE TABLE IF NOT EXISTS "officers" (
    "id" UUID NOT NULL PRIMARY KEY,
    "citizen_id" VARCHAR(255) NOT NULL UNIQUE,
    "first_name" VARCHAR(255) NOT NULL,
    "last_name" VARCHAR(255) NOT NULL,
    "gender" VARCHAR(6) NOT NULL DEFAULT 'other',
    "birth_date" DATE NOT NULL,
    "email" VARCHAR(255),
    "phone" VARCHAR(255),
    "address_number" VARCHAR(100) NOT NULL,
    "village_no" VARCHAR(10),
    "alley" VARCHAR(255),
    "street" VARCHAR(255),
    "postal_code" VARCHAR(5),
    "area_type" VARCHAR(11) NOT NULL,
    "area_code" VARCHAR(255),
    "is_active" BOOL NOT NULL DEFAULT False,
    "approval_date" DATE,
    "approval_by" UUID NOT NULL,
    "approval_status" VARCHAR(8) NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "district_id" VARCHAR(255) REFERENCES "districts" ("district_code") ON DELETE CASCADE,
    "health_area_id" VARCHAR(255) REFERENCES "health_areas" ("code") ON DELETE CASCADE,
    "municipality_id" UUID REFERENCES "municipalities" ("id") ON DELETE CASCADE,
    "position_id" UUID NOT NULL REFERENCES "positions" ("id") ON DELETE CASCADE,
    "prefix_id" UUID NOT NULL REFERENCES "prefixes" ("id") ON DELETE CASCADE,
    "province_id" VARCHAR(255) REFERENCES "provinces" ("province_code") ON DELETE CASCADE,
    "subdistrict_id" VARCHAR(255) REFERENCES "subdistricts" ("subdistrict_code") ON DELETE CASCADE,
    "user_credential_id" UUID NOT NULL REFERENCES "user_credentials" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_officers_citizen_1a52e2" ON "officers" ("citizen_id");
CREATE INDEX IF NOT EXISTS "idx_officers_first_n_b0afa4" ON "officers" ("first_name");
CREATE INDEX IF NOT EXISTS "idx_officers_last_na_ca8365" ON "officers" ("last_name");
CREATE INDEX IF NOT EXISTS "idx_officers_birth_d_2f3cb9" ON "officers" ("birth_date");
CREATE INDEX IF NOT EXISTS "idx_officers_area_co_3c7971" ON "officers" ("area_code");
CREATE INDEX IF NOT EXISTS "idx_officers_approva_482e7d" ON "officers" ("approval_by");
CREATE INDEX IF NOT EXISTS "idx_officers_created_9eff6b" ON "officers" ("created_at");
CREATE INDEX IF NOT EXISTS "idx_officers_updated_5ba87b" ON "officers" ("updated_at");
CREATE INDEX IF NOT EXISTS "idx_officers_deleted_f8465b" ON "officers" ("deleted_at");
CREATE INDEX IF NOT EXISTS "idx_officers_user_cr_1a880e" ON "officers" ("user_credential_id");
COMMENT ON COLUMN "officers"."gender" IS 'MALE: male\nFEMALE: female\nOTHER: other';
COMMENT ON COLUMN "officers"."area_type" IS 'VILLAGE: village\nSUBDISTRICT: subdistrict\nDISTRICT: district\nPROVINCE: province\nAREA: area\nREGION: region\nCOUNTRY: country';
COMMENT ON COLUMN "officers"."approval_status" IS 'PENDING: pending\nAPPROVED: approved\nREJECTED: rejected';
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
