export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    success: boolean;
    access_token: string;
    refresh_token?: string;
    token_type: string;
    expires_in: number;
    scope?: string;
    needs_password_change?: boolean;
}

import type { AdministrativeLevel } from "./officer";

export interface PermissionPage {
    id: string;
    system_name: string;
    main_menu: string;
    sub_main_menu?: string | null;
    allowed_levels: AdministrativeLevel[];
    display_order: number;
    is_active: boolean;
    metadata?: Record<string, unknown> | null;
}

export interface PermissionScopeLevelMeta {
    level: string;
    level_name_th?: string | null;
    level_name_en?: string | null;
}

export interface PermissionScopeCodes {
    health_area_id?: string | null;
    health_service_id?: string | null;
    health_service_name_th?: string | null;
    province_id?: string | null;
    province_name_th?: string | null;
    district_id?: string | null;
    district_name_th?: string | null;
    subdistrict_id?: string | null;
    subdistrict_name_th?: string | null;
    village_code?: string | null;
    village_name_th?: string | null;
    region_code?: string | null;
    osm_code?: string | null;
}

export interface PermissionScope {
    level: AdministrativeLevel | "area";
    level_name_th?: string | null;
    manageable_levels: AdministrativeLevel[];
    manageable_levels_meta?: PermissionScopeLevelMeta[] | null;
    codes: PermissionScopeCodes;
}

export interface UserProfile {
    sub: string;
    user_type: string;
    citizen_id: string;
    name: string;
    phone?: string;
    email?: string;
    birth_date?: string;
    gender?: string;
    client_id: string;
    is_admin?: boolean;
    position_id?: string;
    position_name_th?: string;
    position_scope_level?: string | null;
    province_code?: string;
    province_name?: string;
    district_code?: string;
    district_name?: string;
    subdistrict_code?: string;
    subdistrict_name?: string;
    area_code?: string;
    area_name?: string;
    health_service_id?: string;
    health_service_name_th?: string;
    health_area_code?: string;
    health_area_name?: string;
    region_code?: string;
    region_name?: string;
    permission_scope?: PermissionScope | null;
    is_first_login?: boolean;
    permission_pages?: PermissionPage[];
}

export interface AuthState {
    isAuthenticated: boolean;
    accessToken: string | null;
    refreshToken: string | null;
    user: UserProfile | null;
    expiresAt: number | null;
    mustChangePassword: boolean;
}

export interface ChangePasswordPayload {
    old_password: string;
    new_password: string;
}

export interface ChangePasswordResult {
    success: boolean;
    message: string;
}