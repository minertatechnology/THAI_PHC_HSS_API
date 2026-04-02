import { apiClient } from "./client";

export interface LookupItem {
    id: string;
    label: string;
    name_th?: string;
    name_en?: string;
    code?: string;
    scope_level?: string | null;
    postal_code?: string | null;
    province_code?: string | null;
    district_code?: string | null;
    subdistrict_code?: string | null;
    region_code?: string | null;
    region_name_th?: string | null;
    region_name_en?: string | null;
    position_count?: number;
    health_area_id?: string | null;
}
export interface PositionPayload {
    position_name_th: string;
    position_name_en?: string | null;
    position_code: string;
    scope_level?: string | null;
}

export interface PositionDetail extends PositionPayload {
    id: string;
    label?: string;
    name_th?: string;
    name_en?: string;
    code?: string;
    created_by?: string | null;
    updated_by?: string | null;
    created_at: string;
    updated_at: string;
    deleted_at?: string | null;
}

interface LookupResponse<T = unknown> {
    items: T[];
}

const DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE = [
    "7310dd94-0395-48cb-845b-803279a54f6c",
    "96ca3348-49c2-4d89-903b-32939fd1c95c",
    "f464d614-c20e-4391-84a9-4c8edb7982a9",
];

function normalizeItem(raw: Record<string, unknown>, fallbackKey: string): LookupItem {
    const id = (raw.id ?? raw.code ?? raw[fallbackKey] ?? "") as string;
    const label = (raw.label ?? raw.name_th ?? raw.name_en ?? raw[fallbackKey] ?? raw.code ?? raw.id ?? "") as string;
    return {
        id,
        label,
        name_th: (raw.name_th ?? raw.prefix_name_th ?? raw.province_name_th ?? raw.district_name_th ?? raw.subdistrict_name_th ?? raw.municipality_name_th) as string | undefined,
        name_en: (raw.name_en ?? raw.prefix_name_en ?? raw.province_name_en ?? raw.district_name_en ?? raw.subdistrict_name_en ?? raw.municipality_name_en) as string | undefined,
        code: (raw.code ?? raw.province_code ?? raw.district_code ?? raw.subdistrict_code ?? raw.position_code) as string | undefined,
        scope_level: raw.scope_level as string | undefined,
        postal_code: raw.postal_code as string | undefined,
        province_code: (raw.province_code ?? raw.province_id) as string | undefined,
        district_code: (raw.district_code ?? raw.district_id) as string | undefined,
        subdistrict_code: (raw.subdistrict_code ?? raw.subdistrict_id) as string | undefined,
        region_code: (raw.region_code ?? raw.region_id ?? raw.region) as string | undefined,
        region_name_th: raw.region_name_th as string | undefined,
        region_name_en: raw.region_name_en as string | undefined,
        position_count: typeof raw.position_count === "number" ? (raw.position_count as number) : undefined,
        health_area_id: (raw.health_area_id ?? raw.health_area_code) as string | undefined,
    };
}

export async function fetchPrefixes(keyword?: string): Promise<LookupItem[]> {
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/prefixes", {
        params: keyword ? { keyword } : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "prefix_name_th"));
}

export async function fetchPositions(keyword?: string): Promise<LookupItem[]> {
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/positions", {
        params: keyword ? { keyword } : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "position_name_th"));
}

export async function fetchPositionLevels(): Promise<LookupItem[]> {
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/position-levels");
    return (data.items ?? []).map((item) => normalizeItem(item, "scope_level"));
}

export async function createPosition(payload: PositionPayload): Promise<PositionDetail> {
    const { data } = await apiClient.post<PositionDetail>("/lookups/positions", payload);
    return data;
}

export async function updatePosition(positionId: string, payload: Partial<PositionPayload>): Promise<PositionDetail> {
    const { data } = await apiClient.put<PositionDetail>(`/lookups/positions/${positionId}`, payload);
    return data;
}

export async function deletePosition(positionId: string): Promise<void> {
    await apiClient.delete(`/lookups/positions/${positionId}`);
}

export async function fetchProvinces(keyword?: string): Promise<LookupItem[]> {
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/provinces", {
        params: keyword ? { keyword } : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "province_name_th"));
}

export async function fetchDistricts(provinceCode: string, keyword?: string): Promise<LookupItem[]> {
    if (!provinceCode) {
        return [];
    }
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/districts", {
        params: { province_code: provinceCode, keyword }
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "district_name_th"));
}

export async function fetchSubdistricts(districtCode: string, keyword?: string): Promise<LookupItem[]> {
    if (!districtCode) {
        return [];
    }
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/subdistricts", {
        params: { district_code: districtCode, keyword }
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "subdistrict_name_th"));
}

export async function fetchMunicipalities(params: {
    keyword?: string;
    provinceCode?: string;
    districtCode?: string;
    subdistrictCode?: string;
} = {}): Promise<LookupItem[]> {
    const { keyword, provinceCode, districtCode, subdistrictCode } = params;
    const queryParams: Record<string, string> = {};
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

    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/municipalities", {
        params: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "municipality_name_th"));
}

export async function fetchAreas(keyword?: string): Promise<LookupItem[]> {
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/areas", {
        params: keyword ? { keyword } : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "area_name_th"));
}

export async function fetchHealthAreas(keyword?: string): Promise<LookupItem[]> {
    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>("/lookups/health-areas", {
        params: keyword ? { keyword } : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, "health_area_name_th"));
}

export async function fetchHealthServices(params: {
    keyword?: string;
    provinceCode?: string;
    districtCode?: string;
    subdistrictCode?: string;
    healthServiceTypeIds?: string[];
    healthServiceTypeIdsExclude?: string[];
    limit?: number;
} = {}): Promise<LookupItem[]> {
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
        new Set([...(healthServiceTypeIdsExclude ?? []), ...DEFAULT_HEALTH_SERVICE_TYPE_IDS_EXCLUDE])
    );
    if (mergedExclude.length) {
        queryParams.health_service_type_ids_exclude = mergedExclude;
    }
    if (limit) {
        queryParams.limit = String(limit);
    }

    const { data } = await apiClient.get<LookupResponse<Record<string, unknown>>>('/lookups/health-services', {
        params: Object.keys(queryParams).length > 0 ? queryParams : undefined,
    });
    return (data.items ?? []).map((item) => normalizeItem(item, 'health_service_name_th'));
}
