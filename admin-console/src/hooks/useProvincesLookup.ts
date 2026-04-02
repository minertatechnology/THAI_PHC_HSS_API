import { useEffect, useState } from "react";

import { fetchProvinces, LookupItem } from "../api/lookups";

let cachedProvinces: LookupItem[] | null = null;
let fetchPromise: Promise<LookupItem[]> | null = null;

export function useProvincesLookup() {
    const [items, setItems] = useState<LookupItem[]>(() => cachedProvinces ?? []);
    const [loading, setLoading] = useState<boolean>(!cachedProvinces);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (cachedProvinces) {
            setLoading(false);
            return;
        }
        let cancelled = false;

        if (!fetchPromise) {
            fetchPromise = fetchProvinces().then(
                (data) => {
                    cachedProvinces = data;
                    return data;
                },
                (err) => {
                    fetchPromise = null;
                    throw err;
                }
            );
        }

        setLoading(true);
        fetchPromise
            .then((data) => {
                if (!cancelled) {
                    setItems(data);
                    setError(null);
                    setLoading(false);
                }
            })
            .catch((err: unknown) => {
                if (!cancelled) {
                    setItems([]);
                    setError((err as Error)?.message ?? "โหลดข้อมูลจังหวัดไม่สำเร็จ");
                    setLoading(false);
                }
            });

        return () => {
            cancelled = true;
        };
    }, []);

    return { provinces: items, loading, error };
}

export function primeProvincesCache(data: LookupItem[] | null) {
    if (!data || !Array.isArray(data) || data.length === 0) {
        return;
    }
    cachedProvinces = data;
    fetchPromise = null;
}