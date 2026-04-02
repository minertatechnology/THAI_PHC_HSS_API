import { apiClient } from "./client";
import type { GenHDetail } from "../types/genH";

export async function fetchGenHDetail(userId: string): Promise<GenHDetail> {
    const { data } = await apiClient.get<GenHDetail>(`/gen-h/${userId}`);
    return data;
}
