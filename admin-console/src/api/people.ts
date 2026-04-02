import { apiClient } from "./client";
import type { PeopleDetail } from "../types/people";

export async function fetchPeopleDetail(userId: string): Promise<PeopleDetail> {
    const { data } = await apiClient.get<{ success: boolean; data: PeopleDetail }>(`/people/${userId}`);
    return data.data;
}
