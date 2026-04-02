import { apiClient, ApiRequestConfigInit } from "./client";
import {
  OfficerDetail,
  OfficerCreatePayload,
  OfficerUpdatePayload,
  OfficerQueryParams,
  OfficerPasswordResetResult,
  PaginatedOfficerList,
  OfficerRegistrationMeta,
  OfficerRegistrationPayload,
  OfficerRegistrationResult,
  OfficerApprovalPayload,
  OfficerTransferPayload,
  OfficerTransferHistoryResponse,
} from "../types/officer";
import { LookupItem } from "./lookups";

const OFFICER_BASE = "/officer";

const DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE = [
  "7310dd94-0395-48cb-845b-803279a54f6c",
  "96ca3348-49c2-4d89-903b-32939fd1c95c",
  "f464d614-c20e-4391-84a9-4c8edb7982a9",
];

export async function listOfficers(
  params: OfficerQueryParams = {},
): Promise<PaginatedOfficerList> {
  const { data } = await apiClient.get<PaginatedOfficerList>(OFFICER_BASE, {
    params: {
      ...params,
      limit: params.limit ?? 20,
      page: params.page ?? 1,
      order_by: params.order_by ?? "created_at",
      sort_dir: params.sort_dir ?? "desc",
    },
  });
  return data;
}

export async function fetchOfficer(officerId: string): Promise<OfficerDetail> {
  const { data } = await apiClient.get<{ status: string; data: OfficerDetail }>(
    `${OFFICER_BASE}/${officerId}`,
  );
  return data.data;
}

export async function createOfficer(
  payload: OfficerCreatePayload,
): Promise<OfficerDetail> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerDetail;
  }>(OFFICER_BASE, payload);
  return data.data;
}

export async function updateOfficer(
  officerId: string,
  payload: OfficerUpdatePayload,
): Promise<OfficerDetail> {
  const { data } = await apiClient.put<{ status: string; data: OfficerDetail }>(
    `${OFFICER_BASE}/${officerId}`,
    payload,
  );
  return data.data;
}

export async function transferOfficer(
  officerId: string,
  payload: OfficerTransferPayload,
): Promise<OfficerDetail> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerDetail;
  }>(`${OFFICER_BASE}/${officerId}/transfer`, payload);
  return data.data;
}

export async function fetchOfficerTransferHistory(
  officerId: string,
  params: { page?: number; pageSize?: number } = {},
): Promise<OfficerTransferHistoryResponse> {
  const { page = 1, pageSize = 20 } = params;
  const { data } = await apiClient.get<OfficerTransferHistoryResponse>(
    `${OFFICER_BASE}/${officerId}/transfer-history`,
    { params: { page, page_size: pageSize } },
  );
  return data;
}

type UserLookupSummary = {
  user_id: string;
  first_name?: string | null;
  last_name?: string | null;
  full_name?: string | null;
};

type UserLookupListResponse = {
  items: UserLookupSummary[];
  count: number;
  total: number;
  limit: number;
  offset: number;
};

type UserLookupDetailResponse = {
  success: boolean;
  data?: {
    name?: string | null;
    first_name?: string | null;
    last_name?: string | null;
    full_name?: string | null;
    permission_scope?: {
      level?: string | null;
    } | null;
  } | null;
};

export type OfficerDisplayMeta = {
  name: string | null;
  level: string | null;
};

export async function fetchOfficerDisplayNameById(
  userId: string,
): Promise<string | null> {
  if (!userId) {
    return null;
  }
  const { data } = await apiClient.get<UserLookupListResponse>(
    "/auth/officer/lookups/user-id",
    { params: { user_id: userId, user_type: "officer", limit: 1 } },
  );
  const item = data.items?.[0];
  if (!item) {
    return null;
  }
  if (item.full_name) {
    return item.full_name;
  }
  const combined = [item.first_name, item.last_name].filter(Boolean).join(" ");
  return combined || null;
}

export async function fetchOfficerDisplayMetaById(
  userId: string,
): Promise<OfficerDisplayMeta> {
  if (!userId) {
    return { name: null, level: null };
  }

  const { data } = await apiClient.get<UserLookupDetailResponse>(
    `/auth/officer/lookups/user-id/${userId}`,
    { params: { user_type: "officer" } },
  );

  const detail = data.data;
  const explicitName = detail?.name?.trim() || "";
  const fullName = detail?.full_name?.trim() || "";
  const combinedName = [detail?.first_name, detail?.last_name]
    .filter(Boolean)
    .join(" ")
    .trim();

  return {
    name: explicitName || fullName || combinedName || null,
    level: detail?.permission_scope?.level ?? null,
  };
}

type OfficerBatchResponse = {
  status: string;
  data: OfficerDetail[];
  errors?: Array<{ id: string; error?: string }>;
  message?: string;
};

export async function fetchOfficersByIds(
  ids: string[],
): Promise<OfficerDetail[]> {
  if (!ids.length) {
    return [];
  }
  const { data } = await apiClient.post<OfficerBatchResponse>(
    `${OFFICER_BASE}/batch`,
    { ids },
  );
  return data.data ?? [];
}

export async function setOfficerActiveStatus(
  officerId: string,
  isActive: boolean,
) {
  const { data } = await apiClient.patch<{
    status: string;
    data: OfficerDetail;
  }>(`${OFFICER_BASE}/${officerId}/status`, { is_active: isActive });
  return data.data;
}

export async function deleteOfficer(officerId: string): Promise<void> {
  await apiClient.delete(`${OFFICER_BASE}/${officerId}`);
}

export async function resetOfficerPassword(
  officerId: string,
): Promise<OfficerPasswordResetResult> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerPasswordResetResult;
  }>(`${OFFICER_BASE}/${officerId}/reset-password`);
  return data.data;
}

export async function resetOsmPassword(
  osmId: string,
): Promise<OfficerPasswordResetResult> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerPasswordResetResult;
  }>(`${OFFICER_BASE}/community/osm/${osmId}/reset-password`);
  return data.data;
}

export async function setOsmActiveStatus(
  osmId: string,
  isActive: boolean,
): Promise<{ is_active: boolean }> {
  const { data } = await apiClient.patch<{
    status: string;
    data: { is_active: boolean };
  }>(`${OFFICER_BASE}/community/osm/${osmId}/status`, { is_active: isActive });
  return data.data;
}

export async function resetYuwaPassword(
  userId: string,
): Promise<OfficerPasswordResetResult> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerPasswordResetResult;
  }>(`${OFFICER_BASE}/community/yuwa-osm/${userId}/reset-password`);
  return data.data;
}

export async function resetPeoplePassword(
  userId: string,
): Promise<OfficerPasswordResetResult> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerPasswordResetResult;
  }>(`${OFFICER_BASE}/community/people/${userId}/reset-password`);
  return data.data;
}

export async function setYuwaActiveStatus(
  userId: string,
  isActive: boolean,
): Promise<{ is_active: boolean }> {
  const { data } = await apiClient.patch<{
    status: string;
    data: { is_active: boolean };
  }>(`${OFFICER_BASE}/community/yuwa-osm/${userId}/status`, {
    is_active: isActive,
  });
  return data.data;
}

export async function setPeopleActiveStatus(
  userId: string,
  isActive: boolean,
): Promise<{ is_active: boolean }> {
  const { data } = await apiClient.patch<{
    status: string;
    data: { is_active: boolean };
  }>(`${OFFICER_BASE}/community/people/${userId}/status`, {
    is_active: isActive,
  });
  return data.data;
}

export async function resetGenHPassword(
  userId: string,
): Promise<OfficerPasswordResetResult> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerPasswordResetResult;
  }>(`${OFFICER_BASE}/community/gen-h/${userId}/reset-password`);
  return data.data;
}

export async function setGenHActiveStatus(
  userId: string,
  isActive: boolean,
): Promise<{ is_active: boolean }> {
  const { data } = await apiClient.patch<{
    status: string;
    data: { is_active: boolean };
  }>(`${OFFICER_BASE}/community/gen-h/${userId}/status`, {
    is_active: isActive,
  });
  return data.data;
}

export async function registerOfficer(
  payload: OfficerRegistrationPayload,
): Promise<OfficerRegistrationResult> {
  const config: ApiRequestConfigInit = { skipAuthRefresh: true };
  const { data } = await apiClient.post<OfficerRegistrationResult>(
    `${OFFICER_BASE}/register`,
    payload,
    config,
  );
  return data as OfficerRegistrationResult;
}

export async function fetchOfficerRegistrationMeta(): Promise<OfficerRegistrationMeta> {
  const config: ApiRequestConfigInit = { skipAuthRefresh: true };
  const { data } = await apiClient.get<OfficerRegistrationMeta>(
    `${OFFICER_BASE}/register/meta`,
    config,
  );
  return data;
}

export async function fetchRegistrationPrefixes(
  keyword?: string,
): Promise<LookupItem[]> {
  const config: ApiRequestConfigInit = {
    params: keyword ? { keyword } : undefined,
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/prefixes`,
    config,
  );
  return data.items ?? [];
}

export async function fetchRegistrationDistricts(
  provinceCode: string,
): Promise<LookupItem[]> {
  const config: ApiRequestConfigInit = {
    params: { province_code: provinceCode },
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/districts`,
    config,
  );
  return data.items ?? [];
}

export async function fetchRegistrationSubdistricts(
  districtCode: string,
): Promise<LookupItem[]> {
  const config: ApiRequestConfigInit = {
    params: { district_code: districtCode },
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/subdistricts`,
    config,
  );
  return data.items ?? [];
}

export async function fetchRegistrationMunicipalities(
  params: {
    provinceCode?: string;
    districtCode?: string;
    subdistrictCode?: string;
  } = {},
): Promise<LookupItem[]> {
  const { provinceCode, districtCode, subdistrictCode } = params;
  const queryParams: Record<string, string> = {};
  if (provinceCode) {
    queryParams.province_code = provinceCode;
  }
  if (districtCode) {
    queryParams.district_code = districtCode;
  }
  if (subdistrictCode) {
    queryParams.subdistrict_code = subdistrictCode;
  }
  const config: ApiRequestConfigInit = {
    params: Object.keys(queryParams).length ? queryParams : undefined,
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/municipalities`,
    config,
  );
  return data.items ?? [];
}

export async function fetchRegistrationHealthServices(
  params: {
    keyword?: string;
    provinceCode?: string;
    districtCode?: string;
    subdistrictCode?: string;
    healthServiceTypeIds?: string[];
    healthServiceTypeIdsExclude?: string[];
    limit?: number;
  } = {},
): Promise<LookupItem[]> {
  const {
    keyword,
    provinceCode,
    districtCode,
    subdistrictCode,
    healthServiceTypeIds,
    healthServiceTypeIdsExclude,
    limit,
  } = params;
  const queryParams: Record<string, string | string[]> = {};
  if (keyword) {
    queryParams.keyword = keyword;
  }
  if (provinceCode) {
    queryParams.province_code = provinceCode;
  }
  if (districtCode) {
    queryParams.district_code = districtCode;
  }
  if (subdistrictCode) {
    queryParams.subdistrict_code = subdistrictCode;
  }
  if (healthServiceTypeIds?.length) {
    queryParams.health_service_type_ids = healthServiceTypeIds;
  }
  const mergedExclude = Array.from(
    new Set([
      ...(healthServiceTypeIdsExclude ?? []),
      ...DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE,
    ]),
  );
  if (mergedExclude.length) {
    queryParams.health_service_type_ids_exclude = mergedExclude;
  }
  if (limit) {
    queryParams.limit = String(limit);
  }
  const config: ApiRequestConfigInit = {
    params: Object.keys(queryParams).length ? queryParams : undefined,
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/health-services`,
    config,
  );
  return data.items ?? [];
}

interface LookupResponse<T = LookupItem> {
  items: T[];
}

export async function approveOfficer(
  officerId: string,
  payload: OfficerApprovalPayload = {},
): Promise<OfficerDetail> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerDetail;
  }>(`${OFFICER_BASE}/${officerId}/approve`, payload);
  return data.data;
}

export async function rejectOfficer(
  officerId: string,
  payload: OfficerApprovalPayload = {},
): Promise<OfficerDetail> {
  const { data } = await apiClient.post<{
    status: string;
    data: OfficerDetail;
  }>(`${OFFICER_BASE}/${officerId}/reject`, payload);
  return data.data;
}

export async function fetchRegistrationPositions(
  keyword?: string,
): Promise<LookupItem[]> {
  const config: ApiRequestConfigInit = {
    params: keyword ? { keyword } : undefined,
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/positions`,
    config,
  );
  return data.items ?? [];
}

export async function fetchRegistrationProvinces(
  keyword?: string,
): Promise<LookupItem[]> {
  const config: ApiRequestConfigInit = {
    params: keyword ? { keyword } : undefined,
    skipAuthRefresh: true,
  };
  const { data } = await apiClient.get<LookupResponse>(
    `${OFFICER_BASE}/register/provinces`,
    config,
  );
  return data.items ?? [];
}

export async function fetchRegistrationGenders(): Promise<
  Array<{ code: string; label: string; name_th?: string | null }>
> {
  const config: ApiRequestConfigInit = { skipAuthRefresh: true };
  const { data } = await apiClient.get<
    LookupResponse<{ code: string; label: string; name_th?: string | null }>
  >(`${OFFICER_BASE}/register/genders`, config);
  return data.items ?? [];
}
