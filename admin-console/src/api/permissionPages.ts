import { apiClient } from "./client";
import type { PermissionPage } from "../types/auth";
import type { AdministrativeLevel } from "../types/officer";

export interface PermissionPagePayload {
    system_name?: string;
    main_menu: string;
    sub_main_menu?: string | null;
    allowed_levels: AdministrativeLevel[];
    display_order?: number;
    is_active?: boolean;
    metadata?: Record<string, unknown> | null;
}

export interface PermissionPageUpdatePayload {
    main_menu?: string;
    sub_main_menu?: string | null;
    allowed_levels?: AdministrativeLevel[];
    display_order?: number;
    is_active?: boolean;
    metadata?: Record<string, unknown> | null;
}

export async function fetchPermissionPages(includeInactive = false, systemName?: string): Promise<PermissionPage[]> {
    const params: Record<string, string | boolean> = { include_inactive: includeInactive };
    if (systemName) {
        params.system_name = systemName;
    }
    const { data } = await apiClient.get<PermissionPage[]>("/auth/permission-pages", { params });
    return data;
}

export async function createPermissionPage(payload: PermissionPagePayload): Promise<PermissionPage> {
    const { data } = await apiClient.post<PermissionPage>("/auth/permission-pages", payload);
    return data;
}

export async function updatePermissionPage(pageId: string, payload: PermissionPageUpdatePayload): Promise<PermissionPage> {
    const { data } = await apiClient.put<PermissionPage>(`/auth/permission-pages/${pageId}`, payload);
    return data;
}

export async function deletePermissionPage(pageId: string): Promise<void> {
    await apiClient.delete(`/auth/permission-pages/${pageId}`);
}
