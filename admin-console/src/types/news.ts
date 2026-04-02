export type Platform = "SmartOSM" | "ThaiPHC";

export interface NewsArticle {
    id: string;
    title: string;
    department: string;
    content_html: string;
    image_urls: string[];
    platforms: Platform[];
    created_at: string;
    updated_at: string;
    created_by?: string | null;
    updated_by?: string | null;
}

export interface NewsFormData {
    title: string;
    department: string;
    content: string;
    platforms: Platform[];
    images?: File[];
}

export interface NewsUpdateFormData extends NewsFormData {
    existing_image_urls?: string[];
}
