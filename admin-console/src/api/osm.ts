import { apiClient } from "./client";
import type { OsmProfileDetail } from "../types/osm";
import type { YuwaOsmDetail } from "../types/yuwaOsm";

export async function fetchOsmDetail(osmId: string): Promise<OsmProfileDetail> {
    const { data } = await apiClient.get<{ status: string; data: OsmProfileDetail }>(`/osm/${osmId}`);
    return data.data;
}

export async function fetchYuwaOsmDetail(userId: string): Promise<YuwaOsmDetail> {
    const { data } = await apiClient.get<{ success: boolean; data: YuwaOsmDetail }>(`/yuwa-osm/${userId}`);
    return data.data;
}
