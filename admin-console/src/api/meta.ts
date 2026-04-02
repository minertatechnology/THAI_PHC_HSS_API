import { apiClient } from "./client";

export interface MetaItem {
    code: string;
    name_th?: string;
    name_en?: string;
    [key: string]: unknown;
}

export async function fetchMetaItems(collection: string): Promise<MetaItem[]> {
    const { data } = await apiClient.get<{ success: boolean; items: MetaItem[] }>(`/meta/${collection}`);
    return data.items ?? [];
}

export async function fetchPrefixItems() {
    return fetchMetaItems("prefixes");
}

export async function fetchPositionItems() {
    return fetchMetaItems("positions");
}

export async function fetchGenderItems() {
    return fetchMetaItems("genders");
}