import { UserProfile } from "../types/auth";

const normalizeScopeLevel = (value: string | null | undefined): string | null =>
    typeof value === "string" ? value.toLowerCase() : null;

const isOfficerWithScope = (user: UserProfile | null | undefined, allowedLevels: Set<string>): boolean => {
    if (!user || user.user_type !== "officer") {
        return false;
    }
    const scopeLevel = normalizeScopeLevel(user.position_scope_level);
    if (!scopeLevel) {
        return false;
    }
    return allowedLevels.has(scopeLevel);
};

const ACCESS_CONTROL_LEVELS = new Set(["country", "department"]);
const DEPARTMENT_LOOKUP_LEVELS = new Set(["country", "area"]);

export const canManageClientAccess = (user: UserProfile | null | undefined): boolean =>
    isOfficerWithScope(user, ACCESS_CONTROL_LEVELS);

export const canUseDepartmentLookups = (user: UserProfile | null | undefined): boolean =>
    isOfficerWithScope(user, DEPARTMENT_LOOKUP_LEVELS);
