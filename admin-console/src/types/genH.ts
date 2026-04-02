export interface GenHDetail {
    id: string;
    gen_h_code?: string | null;
    prefix?: string | null;
    first_name: string;
    last_name: string;
    gender?: string | null;
    phone_number?: string | null;
    email?: string | null;
    line_id?: string | null;
    school?: string | null;
    province_code?: string | null;
    province_name?: string | null;
    district_code?: string | null;
    district_name?: string | null;
    subdistrict_code?: string | null;
    subdistrict_name?: string | null;
    profile_image_url?: string | null;
    member_card_url?: string | null;
    points: number;
    is_active: boolean;
    people_user_id?: string | null;
    yuwa_osm_user_id?: string | null;
    transferred_at?: string | null;
    created_at?: string | null;
    updated_at?: string | null;
}
