import { LookupItem } from "../api/lookups";

export type AdministrativeLevel =
  | "village"
  | "subdistrict"
  | "district"
  | "province"
  | "area"
  | "region"
  | "country";

export type OfficerApprovalStatus = "pending" | "approved" | "rejected";

export interface OfficerPermissions {
  can_edit: boolean;
  can_toggle_active: boolean;
  can_reset_password: boolean;
  can_delete: boolean;
  can_approve: boolean;
  can_manage: boolean;
  can_transfer?: boolean;
  is_self: boolean;
  is_same_level: boolean;
}

export interface OfficerListItem {
  id: string;
  citizen_id: string;
  prefix_name_th?: string | null;
  first_name: string;
  last_name: string;
  profile_image?: string | null;
  position_name_th?: string | null;
  health_service_id?: string | null;
  health_service_name_th?: string | null;
  province_name_th?: string | null;
  district_name_th?: string | null;
  subdistrict_name_th?: string | null;
  area_type?: AdministrativeLevel | null;
  area_code?: string | null;
  approval_status: OfficerApprovalStatus;
  is_active: boolean;
  permissions?: OfficerPermissions;
}

export interface OfficerDetail {
  id: string;
  citizen_id: string;
  prefix_id: string;
  prefix_name_th?: string | null;
  first_name: string;
  last_name: string;
  gender?: string | null;
  birth_date?: string | null;
  email?: string | null;
  phone?: string | null;
  profile_image?: string | null;
  position_id: string;
  position_name_th?: string | null;
  address_number: string;
  alley?: string | null;
  street?: string | null;
  village_no?: string | null;
  postal_code?: string | null;
  province_id?: string | null;
  province_name_th?: string | null;
  district_id?: string | null;
  district_name_th?: string | null;
  subdistrict_id?: string | null;
  subdistrict_name_th?: string | null;
  municipality_id?: string | null;
  municipality_name_th?: string | null;
  health_area_id?: string | null;
  health_area_name_th?: string | null;
  health_service_id?: string | null;
  health_service_name_th?: string | null;
  area_type?: AdministrativeLevel | null;
  area_code?: string | null;
  is_active: boolean;
  approval_status: OfficerApprovalStatus;
  approval_by?: string | null;
  approval_date?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  deleted_at?: string | null;
  permissions?: OfficerPermissions;
}

export interface OfficerCreatePayload {
  citizen_id: string;
  prefix_id: string;
  first_name: string;
  last_name: string;
  gender?: string;
  birth_date?: string;
  email?: string;
  phone?: string;
  profile_image?: string;
  position_id: string;
  address_number: string;
  province_id?: string;
  district_id?: string;
  subdistrict_id?: string;
  village_no?: string;
  alley?: string;
  street?: string;
  postal_code?: string;
  municipality_id?: string;
  health_area_id?: string;
  health_service_id?: string;
  area_type?: AdministrativeLevel;
  area_code?: string;
  password: string;
}

export type OfficerUpdatePayload = Partial<
  Omit<
    OfficerCreatePayload,
    | "password"
    | "citizen_id"
    | "position_id"
    | "prefix_id"
    | "birth_date"
    | "gender"
  >
> & {
  position_id?: string;
  prefix_id?: string;
  gender?: string;
  birth_date?: string;
};

export interface OfficerQueryParams {
  search?: string;
  area_code?: string;
  health_service_id?: string;
  position_id?: string;
  province_id?: string;
  district_id?: string;
  subdistrict_id?: string;
  is_active?: boolean;
  approval_status?: OfficerApprovalStatus | string;
  page?: number;
  limit?: number;
  order_by?: string;
  sort_dir?: "asc" | "desc";
}

export interface OfficerPasswordResetResult {
  temporary_password: string;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

export interface PaginatedOfficerList {
  items: OfficerListItem[];
  pagination: PaginationMeta;
}

export interface OfficerRegistrationMeta {
  prefixes: LookupItem[];
  genders: Array<{ code: string; label: string; name_th?: string | null }>;
  positions: LookupItem[];
  provinces: LookupItem[];
  health_areas: LookupItem[];
  areas: LookupItem[];
  regions: LookupItem[];
}

export type OfficerRegistrationPayload = OfficerCreatePayload;

export interface OfficerRegistrationResult {
  status: string;
  message: string;
  data?: { id: string };
}

export interface OfficerApprovalPayload {
  note?: string;
}

export interface OfficerTransferPayload {
  health_area_id?: string | null;
  province_id?: string | null;
  district_id?: string | null;
  subdistrict_id?: string | null;
  health_service_id?: string | null;
  note?: string | null;
}

export interface OfficerTransferHistoryItem {
  id: string;
  timestamp: string;
  action: string;
  description?: string | null;
  by?: string | null;
  success: boolean;
  old_data?: Record<string, unknown> | null;
  new_data?: Record<string, unknown> | null;
}

export interface OfficerTransferHistoryResponse {
  status: string;
  message: string;
  items: OfficerTransferHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}
