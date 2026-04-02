import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  canManageClientAccess,
  canUseDepartmentLookups,
} from "../utils/permissions";
import ForcedPasswordChangeDialog from "./ForcedPasswordChangeDialog";

export const Layout: React.FC<{ children: React.ReactNode }> = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { user, logout, mustChangePassword } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [isMenuOpen, setMenuOpen] = useState(false);

  const canManageAccess = canManageClientAccess(user);
  const canUseLookups = canUseDepartmentLookups(user);

  // สร้างข้อความแสดงพื้นที่รับผิดชอบตาม scope level
  // ระดับกรมขึ้นไป (department, ministry, central) ไม่ต้องแสดง
  const hiddenScopes = new Set(["department", "ministry", "central", "national"]);

  const getAreaLabel = (): string | null => {
    if (!user) return null;
    const scope = user.position_scope_level;
    if (scope && hiddenScopes.has(scope)) return null;

    const parts: string[] = [];

    if (scope === "area" || scope === "health_area") {
      if (user.health_area_name) parts.push(user.health_area_name);
    } else if (scope === "province") {
      if (user.province_name) parts.push(`จ.${user.province_name}`);
    } else if (scope === "district") {
      if (user.district_name) parts.push(`อ.${user.district_name}`);
      if (user.province_name) parts.push(`จ.${user.province_name}`);
    } else if (scope === "subdistrict") {
      if (user.subdistrict_name) parts.push(`ต.${user.subdistrict_name}`);
      if (user.district_name) parts.push(`อ.${user.district_name}`);
      if (user.province_name) parts.push(`จ.${user.province_name}`);
    } else {
      if (user.province_name) parts.push(`จ.${user.province_name}`);
    }

    return parts.length > 0 ? parts.join(" ") : null;
  };

  const areaLabel = getAreaLabel();
  const healthServiceLabel = user?.health_service_name_th ?? null;
  // tooltip: รวมทั้งพื้นที่ + หน่วยบริการ แบบเต็ม
  const fullAreaTooltip = [areaLabel, healthServiceLabel].filter(Boolean).join(" | ") || undefined;

  const handleLogout = async () => {
    await logout();
  };

  const isActive = (path: string) => location.pathname.startsWith(path);

  const handleProfileNavigate = () => {
    navigate("/profile");
    setMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-sm">
              <span className="text-lg font-semibold">OA</span>
            </div>
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
                Officer Admin Console
              </p>
              <p className="text-sm text-slate-500">
                ระบบจัดการเจ้าหน้าที่สาธารณสุข
              </p>
            </div>
          </div>
          <nav className="hidden items-center gap-2 md:flex">
            <Link
              to="/officers"
              className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                isActive("/officers")
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              รายการเจ้าหน้าที่
            </Link>
            {canUseLookups && (
              <Link
                to="/search/community"
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive("/search/community")
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                ค้นหา อสม./ยุวอสม.
              </Link>
            )}
            {canManageAccess && (
              <Link
                to="/access-control"
                className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive("/access-control")
                    ? "bg-emerald-50 text-emerald-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                สิทธิ์การเข้าระบบ
              </Link>
            )}
          </nav>
          <div className="relative flex items-center gap-3">
            <button
              onClick={() => setMenuOpen((prev) => !prev)}
              title={fullAreaTooltip}
              className="flex max-w-[220px] flex-col items-end rounded-lg px-3 py-2 text-right transition hover:bg-slate-100"
            >
              <span className="text-sm font-semibold text-slate-900">
                {user?.name ?? "Officer"}
              </span>
              <span className="text-xs text-slate-500">
                {user?.position_name_th ?? "เจ้าหน้าที่"}
              </span>
              {areaLabel && (
                <span className="w-full truncate text-xs text-blue-600">
                  {areaLabel}
                </span>
              )}
              {healthServiceLabel && (
                <span className="w-full truncate text-xs text-slate-400">
                  {healthServiceLabel}
                </span>
              )}
            </button>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 hover:text-slate-900"
            >
              Logout
            </button>
            {isMenuOpen && (
              <div className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-slate-200 bg-white py-2 shadow-lg">
                <button
                  onClick={handleProfileNavigate}
                  className={`block w-full px-4 py-2 text-left text-sm font-medium transition ${
                    isActive("/profile")
                      ? "text-blue-700"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                >
                  โปรไฟล์ของฉัน
                </button>
                {canManageAccess && (
                  <Link
                    to="/access-control"
                    onClick={() => setMenuOpen(false)}
                    className={`block w-full px-4 py-2 text-left text-sm font-medium transition ${
                      isActive("/access-control")
                        ? "text-emerald-700"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    จัดการสิทธิ์ระบบ
                  </Link>
                )}
                {canUseLookups && (
                  <Link
                    to="/search/community"
                    onClick={() => setMenuOpen(false)}
                    className={`block w-full px-4 py-2 text-left text-sm font-medium transition ${
                      isActive("/search/community")
                        ? "text-emerald-700"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    ค้นหา อสม./ยุวอสม.
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-screen-2xl px-2 py-6 sm:px-3 lg:px-4">
        {children}
      </main>
      {mustChangePassword && <ForcedPasswordChangeDialog />}
    </div>
  );
};
