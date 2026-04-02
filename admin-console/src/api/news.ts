import { api } from "./client";
import { NewsArticle, NewsFormData, NewsUpdateFormData } from "../types/news";

export interface ListNewsParams {
    limit?: number;
    offset?: number;
}

export const newsApi = {
    async list(params: ListNewsParams = {}): Promise<NewsArticle[]> {
        const { limit = 20, offset = 0 } = params;
        const response = await api.get("/news/", { params: { limit, offset } });
        return response.data;
    },

    async create(data: NewsFormData): Promise<NewsArticle> {
        const formData = new FormData();
        formData.append("title", data.title);
        formData.append("department", data.department);
        formData.append("content", data.content);

        // Add platforms as separate form fields
        if (data.platforms && data.platforms.length > 0) {
            data.platforms.forEach(platform => {
                formData.append("platforms", platform);
            });
        }

        // Add images if any
        if (data.images && data.images.length > 0) {
            data.images.forEach(image => {
                formData.append("images", image);
            });
        }

        const response = await api.post("/news/", formData);
        return response.data;
    },

    async update(newsId: string, data: NewsUpdateFormData): Promise<NewsArticle> {
        const formData = new FormData();
        formData.append("title", data.title);
        formData.append("department", data.department);
        formData.append("content", data.content);

        // Add platforms as separate form fields
        if (data.platforms && data.platforms.length > 0) {
            data.platforms.forEach(platform => {
                formData.append("platforms", platform);
            });
        }

        // Add existing image URLs if any
        if (data.existing_image_urls && data.existing_image_urls.length > 0) {
            data.existing_image_urls.forEach(url => {
                formData.append("existing_image_urls", url);
            });
        }

        // Add new images if any
        if (data.images && data.images.length > 0) {
            data.images.forEach(image => {
                formData.append("images", image);
            });
        }

        const response = await api.put(`/news/${newsId}`, formData);
        return response.data;
    },

    async delete(newsId: string): Promise<void> {
        await api.delete(`/news/${newsId}`);
    },
};
