import { apiClient } from "./client";
import {
  OAuthClientSummary,
  UpdateClientUserTypesPayload,
  CreateOAuthClientPayload,
  UpdateOAuthClientPayload,
  ClientBlockEntry,
  CreateClientBlockPayload,
  ClientBlockCandidate,
  PaginatedBlockCandidates,
  ClientAllowEntry,
  UpdateClientAllowlistModePayload,
  CreateClientAllowPayload,
  UserType,
} from "../types/oauthClient";

const BASE = "/auth/clients";

/**
 * Fetches allowed domains for registration return URL validation
 * Uses public endpoint (no authentication required)
 */
export async function fetchAllowedRegistrationDomains(): Promise<string[]> {
  try {
    const { data } = await apiClient.get<string[]>(`${BASE}/allowed-domains`);
    return data;
  } catch (error) {
    console.error('Failed to fetch allowed domains:', error);
    // Fallback to localhost only if API fails
    return ['localhost', '127.0.0.1'];
  }
}

export async function fetchOAuthClients(): Promise<OAuthClientSummary[]> {
  const { data } = await apiClient.get<OAuthClientSummary[]>(BASE);
  return data;
}

export async function updateOAuthClientUserTypes(
  clientId: string,
  payload: UpdateClientUserTypesPayload
): Promise<OAuthClientSummary> {
  const { data } = await apiClient.put<OAuthClientSummary>(
    `${BASE}/${clientId}/allowed-user-types`,
    payload
  );
  return data;
}

export async function resetOAuthClientUserTypesToDefault(
  clientId: string
): Promise<OAuthClientSummary> {
  const { data } = await apiClient.post<OAuthClientSummary>(
    `${BASE}/${clientId}/allowed-user-types/reset-default`
  );
  return data;
}

export async function createOAuthClient(
  payload: CreateOAuthClientPayload
): Promise<OAuthClientSummary> {
  const { data } = await apiClient.post<OAuthClientSummary>(BASE, payload);
  return data;
}

export async function updateOAuthClient(
  clientId: string,
  payload: UpdateOAuthClientPayload
): Promise<OAuthClientSummary> {
  const { data } = await apiClient.put<OAuthClientSummary>(
    `${BASE}/${clientId}`,
    payload
  );
  return data;
}

export async function fetchClientBlocks(
  clientId: string,
  params?: { search?: string; userType?: UserType }
): Promise<ClientBlockEntry[]> {
  const query: Record<string, string> = {};
  if (params?.search) {
    query.search = params.search;
  }
  if (params?.userType) {
    query.user_type = params.userType;
  }

  const { data } = await apiClient.get<ClientBlockEntry[]>(
    `${BASE}/${clientId}/blocks`,
    { params: query }
  );
  return data;
}

export async function createClientBlock(
  clientId: string,
  payload: CreateClientBlockPayload
): Promise<ClientBlockEntry> {
  const { data } = await apiClient.post<ClientBlockEntry>(
    `${BASE}/${clientId}/blocks`,
    payload
  );
  return data;
}

export async function deleteClientBlock(
  clientId: string,
  blockId: string
): Promise<void> {
  await apiClient.delete(`${BASE}/${clientId}/blocks/${blockId}`);
}

export async function searchClientBlockCandidates(params: {
  userType: UserType;
  query: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedBlockCandidates> {
  const query: Record<string, string | number> = {
    user_type: params.userType,
    query: params.query,
  };
  if (params.limit !== undefined) {
    query.limit = params.limit;
  }
  if (params.offset !== undefined) {
    query.offset = params.offset;
  }

  const { data } = await apiClient.get<PaginatedBlockCandidates>(
    `${BASE}/block-candidates`,
    { params: query }
  );
  return data;
}

export async function updateOAuthClientAllowlistMode(
  clientId: string,
  payload: UpdateClientAllowlistModePayload
): Promise<OAuthClientSummary> {
  const { data } = await apiClient.put<OAuthClientSummary>(
    `${BASE}/${clientId}/allowlist-mode`,
    payload
  );
  return data;
}

export async function fetchClientAllows(
  clientId: string,
  params?: { search?: string; userType?: UserType }
): Promise<ClientAllowEntry[]> {
  const query: Record<string, string> = {};
  if (params?.search) {
    query.search = params.search;
  }
  if (params?.userType) {
    query.user_type = params.userType;
  }
  const { data } = await apiClient.get<ClientAllowEntry[]>(
    `${BASE}/${clientId}/allows`,
    { params: query }
  );
  return data;
}

export async function createClientAllow(
  clientId: string,
  payload: CreateClientAllowPayload
): Promise<ClientAllowEntry> {
  const { data } = await apiClient.post<ClientAllowEntry>(
    `${BASE}/${clientId}/allows`,
    payload
  );
  return data;
}

export async function deleteClientAllow(
  clientId: string,
  allowId: string
): Promise<void> {
  await apiClient.delete(`${BASE}/${clientId}/allows/${allowId}`);
}
