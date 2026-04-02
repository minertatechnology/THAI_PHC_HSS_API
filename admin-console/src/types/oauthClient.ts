export type UserType = "officer" | "osm" | "yuwa_osm" | "people" | "gen_h";

export interface OAuthClientSummary {
  id: string;
  client_id: string;
  client_name: string;
  client_description?: string | null;
  redirect_uri: string;
  login_url?: string | null;
  login_url_example?: string | null;
  consent_url?: string | null;
  consent_url_example?: string | null;
  scopes: string[];
  grant_types: string[];
  public_client: boolean;
  allowed_user_types: UserType[] | null;
  allowlist_enabled?: boolean;
  is_active: boolean;
}

export interface UpdateClientUserTypesPayload {
  allowed_user_types: UserType[] | null;
}

export interface CreateOAuthClientPayload {
  client_name: string;
  client_description?: string | null;
  redirect_uri: string;
  login_url: string;
  consent_url: string;
  scopes: string[];
  grant_types: string[];
  public_client: boolean;
}

export interface UpdateOAuthClientPayload {
  client_name: string;
  client_description?: string | null;
  redirect_uri: string;
  login_url: string;
  consent_url: string;
  scopes: string[];
  grant_types: string[];
  public_client: boolean;
}

export interface ClientBlockEntry {
  id: string;
  client_id: string;
  client_uuid: string;
  user_id: string;
  user_type: UserType;
  citizen_id: string | null;
  full_name: string | null;
  note?: string | null;
  created_by?: string | null;
  created_at: string;
}

export interface ClientAllowEntry {
  id: string;
  client_id: string;
  client_uuid: string;
  user_id: string;
  user_type: UserType;
  citizen_id: string | null;
  full_name: string | null;
  note?: string | null;
  created_by?: string | null;
  created_at: string;
}

export interface UpdateClientAllowlistModePayload {
  allowlist_enabled: boolean;
}

export interface CreateClientAllowPayload {
  user_id: string;
  user_type: UserType;
  note?: string;
}

export interface CreateClientBlockPayload {
  user_id: string;
  user_type: UserType;
  note?: string;
}

export interface ClientBlockCandidate {
  user_id: string;
  user_type: UserType;
  full_name: string;
  citizen_id?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
  is_transferred?: boolean | null;
  transferred_at?: string | null;
  transferred_by?: string | null;
  yuwa_osm_id?: string | null;
  yuwa_osm_code?: string | null;
  province_name?: string | null;
  district_name?: string | null;
  subdistrict_name?: string | null;
  organization?: string | null;
  role?: string | null;
  province_code?: string | null;
  district_code?: string | null;
  subdistrict_code?: string | null;
  village_code?: string | null;
  region_code?: string | null;
  health_area_code?: string | null;
}

export interface PaginatedBlockCandidates {
  items: ClientBlockCandidate[];
  total: number;
  limit: number;
  offset: number;
}
