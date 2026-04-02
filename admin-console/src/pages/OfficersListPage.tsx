import React, { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  listOfficers,
  setOfficerActiveStatus,
  approveOfficer,
  rejectOfficer,
} from "../api/officers";
import {
  OfficerListItem,
  OfficerQueryParams,
  OfficerApprovalStatus,
  PaginatedOfficerList,
  AdministrativeLevel,
} from "../types/officer";
import {
  SensitiveValue,
  EyeIcon,
  EyeOffIcon,
} from "../components/ui/SensitiveValue";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { PageLoader } from "../components/ui/PageLoader";
import { useAuthContext } from "../context/AuthContext";
import { useProvincesLookup } from "../hooks/useProvincesLookup";
import { fetchPositions, LookupItem } from "../api/lookups";

const DEFAULT_PAGE_SIZE = 20;

type IconProps = { className?: string };

const IconSpinner = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={`${className} animate-spin`}
    fill="none"
  >
    <circle
      cx="12"
      cy="12"
      r="9"
      stroke="currentColor"
      strokeWidth={2}
      strokeOpacity={0.2}
    />
    <path
      d="M21 12a9 9 0 0 0-9-9"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
    />
  </svg>
);

const IconCheck = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m6 12.5 4.5 4.5L18 9"
    />
  </svg>
);

const IconX = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M6 6l12 12M6 18 18 6"
    />
  </svg>
);

const IconPower = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.8}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3v7" />
    <path d="M7.5 5.6A9 9 0 1 0 18 8" />
  </svg>
);

type IconButtonTone = "neutral" | "info" | "success" | "warning" | "danger";

const ICON_BASE_CLASS =
  "inline-flex h-9 w-9 items-center justify-center rounded-lg border text-sm transition focus:outline-none focus:ring-2 focus:ring-blue-100 focus:ring-offset-1";

const ICON_TONE_CLASS: Record<IconButtonTone, string> = {
  neutral:
    "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-100",
  info: "border-blue-200 bg-blue-50 text-blue-600 hover:border-blue-300 hover:bg-blue-100",
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-600 hover:border-emerald-300 hover:bg-emerald-100",
  warning:
    "border-amber-200 bg-amber-50 text-amber-600 hover:border-amber-300 hover:bg-amber-100",
  danger:
    "border-rose-200 bg-rose-50 text-rose-600 hover:border-rose-300 hover:bg-rose-100",
};

type IconButtonProps = {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  tone?: IconButtonTone;
  busy?: boolean;
  children: React.ReactNode;
};

const IconButton: React.FC<IconButtonProps> = ({
  label,
  onClick,
  disabled = false,
  tone = "neutral",
  busy = false,
  children,
}) => {
  const disabledClass = disabled ? "cursor-not-allowed opacity-50" : "";
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`${ICON_BASE_CLASS} ${ICON_TONE_CLASS[tone]} ${disabledClass}`.trim()}
      disabled={disabled}
    >
      {busy ? <IconSpinner className="h-4 w-4" /> : children}
      <span className="sr-only">{label}</span>
    </button>
  );
};

type IconActionLinkProps = {
  label: string;
  to: string;
  tone?: IconButtonTone;
  children: React.ReactNode;
};

const IconActionLink: React.FC<IconActionLinkProps> = ({
  label,
  to,
  tone = "info",
  children,
}) => (
  <Link
    to={to}
    aria-label={label}
    title={label}
    className={`${ICON_BASE_CLASS} ${ICON_TONE_CLASS[tone]}`}
  >
    {children}
    <span className="sr-only">{label}</span>
  </Link>
);
type StatusFilter = "all" | "active" | "inactive";
type ApprovalFilter = "all" | "approved" | "pending" | "rejected";

const STATUS_FILTER_OPTIONS: ReadonlyArray<{
  value: StatusFilter;
  label: string;
}> = [
  { value: "all", label: "ทั้งหมด" },
  { value: "active", label: "เปิดใช้งาน" },
  { value: "inactive", label: "ปิดใช้งาน" },
];

const APPROVAL_FILTER_OPTIONS: ReadonlyArray<{
  value: ApprovalFilter;
  label: string;
}> = [
  { value: "all", label: "ทั้งหมด" },
  { value: "approved", label: "อนุมัติแล้ว" },
  { value: "pending", label: "รออนุมัติ" },
  { value: "rejected", label: "ปฏิเสธ" },
];

const APPROVAL_STATUS_LABELS: Record<OfficerApprovalStatus, string> = {
  approved: "อนุมัติแล้ว",
  pending: "รออนุมัติ",
  rejected: "ปฏิเสธแล้ว",
};

const APPROVAL_STATUS_BADGE_CLASSES: Record<OfficerApprovalStatus, string> = {
  approved: "bg-emerald-100 text-emerald-700",
  pending: "bg-amber-100 text-amber-700",
  rejected: "bg-rose-100 text-rose-700",
};

type ConfirmActionType = "toggle" | "approve" | "reject";

export const OfficersListPage: React.FC = () => {
  const { user } = useAuthContext();
  const [searchParams, setSearchParams] = useSearchParams();

  const enforcedProvinceFilter = useMemo(() => {
    if (!user?.permission_scope) {
      return null;
    }
    const managedLevels: AdministrativeLevel[] = [
      "province",
      "district",
      "subdistrict",
      "village",
    ];
    const scopeLevel = user.permission_scope.level as
      | AdministrativeLevel
      | undefined;
    if (!scopeLevel || !managedLevels.includes(scopeLevel)) {
      return null;
    }
    const codes = user.permission_scope.codes ?? {};
    return codes.province_id ?? user.province_code ?? null;
  }, [user]);

  const enforcedProvinceLabel = useMemo(() => {
    if (!enforcedProvinceFilter) {
      return null;
    }
    return (
      user?.permission_scope?.codes?.province_name_th ??
      user?.province_name ??
      null
    );
  }, [enforcedProvinceFilter, user]);

  const [officers, setOfficers] = useState<OfficerListItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const initialQuery = (searchParams.get("q") ?? "").trim();
  const initialHealthServiceCode = (searchParams.get("hsc") ?? "").trim();
  const initialStatus = (searchParams.get("status") as StatusFilter | null) ?? "all";
  const initialApproval = (searchParams.get("approval") as ApprovalFilter | null) ?? "all";
  const initialPosition = (searchParams.get("position") ?? "all").trim() || "all";
  const initialProvince = (searchParams.get("province") ?? "all").trim() || "all";
  const initialPageRaw = Number(searchParams.get("page") ?? "1");
  const initialPage = Number.isFinite(initialPageRaw) && initialPageRaw > 0 ? Math.floor(initialPageRaw) : 1;

  const [searchTerm, setSearchTerm] = useState<string>(initialQuery);
  const [healthServiceCodeTerm, setHealthServiceCodeTerm] =
    useState<string>(initialHealthServiceCode);
  const [query, setQuery] = useState<string>(initialQuery);
  const [healthServiceCodeQuery, setHealthServiceCodeQuery] =
    useState<string>(initialHealthServiceCode);
  const [refreshToken, setRefreshToken] = useState<number>(0);
  const [busyOfficerId, setBusyOfficerId] = useState<string | null>(null);
  const [confirmState, setConfirmState] = useState<{
    type: ConfirmActionType;
    officer: OfficerListItem;
  } | null>(null);
  const [actionBusy, setActionBusy] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(
    STATUS_FILTER_OPTIONS.some((item) => item.value === initialStatus)
      ? initialStatus
      : "all",
  );
  const [approvalFilter, setApprovalFilter] = useState<ApprovalFilter>(
    APPROVAL_FILTER_OPTIONS.some((item) => item.value === initialApproval)
      ? initialApproval
      : "all",
  );
  const [positionFilter, setPositionFilter] = useState<string>(initialPosition);
  const [positions, setPositions] = useState<LookupItem[]>([]);
  const [loadingPositions, setLoadingPositions] = useState<boolean>(false);
  const [positionsError, setPositionsError] = useState<string | null>(null);
  const [provinceFilter, setProvinceFilter] = useState<string>(
    () => enforcedProvinceFilter ?? initialProvince,
  );
  const {
    provinces,
    loading: loadingProvinces,
    error: provincesError,
  } = useProvincesLookup();
  const [page, setPage] = useState<number>(initialPage);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const pendingRequestRef = useRef<{
    key: string;
    promise: Promise<PaginatedOfficerList>;
  } | null>(null); // reuse in-flight load to avoid duplicate calls

  const isProvinceFilterLocked = useMemo(
    () => Boolean(enforcedProvinceFilter),
    [enforcedProvinceFilter],
  );

  const filteredPositions = useMemo(() => {
    const excludedNames = new Set(["ระดับหมู่บ้าน", "ผู้อำนวยการ"]);
    return positions.filter((position) => {
      const label = (position.name_th ?? position.label ?? "").trim();
      return !excludedNames.has(label);
    });
  }, [positions]);

  const provinceOptions = useMemo(() => {
    if (!isProvinceFilterLocked || !enforcedProvinceFilter) {
      return provinces;
    }
    const exists = provinces.some((item) => item.id === enforcedProvinceFilter);
    if (exists) {
      return provinces;
    }
    const fallbackLabel = enforcedProvinceLabel ?? "จังหวัดของฉัน";
    return [{ id: enforcedProvinceFilter, label: fallbackLabel }, ...provinces];
  }, [
    provinces,
    isProvinceFilterLocked,
    enforcedProvinceFilter,
    enforcedProvinceLabel,
  ]);

  useEffect(() => {
    let isCurrent = true;
    setLoadingPositions(true);
    setPositionsError(null);
    fetchPositions()
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        setPositions(items);
      })
      .catch(() => {
        if (!isCurrent) {
          return;
        }
        setPositionsError("โหลดข้อมูลตำแหน่งไม่สำเร็จ");
      })
      .finally(() => {
        if (!isCurrent) {
          return;
        }
        setLoadingPositions(false);
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    if (enforcedProvinceFilter && provinceFilter !== enforcedProvinceFilter) {
      setProvinceFilter(enforcedProvinceFilter);
    }
  }, [enforcedProvinceFilter, provinceFilter]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (query) {
      params.set("q", query);
    }
    if (healthServiceCodeQuery) {
      params.set("hsc", healthServiceCodeQuery);
    }
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (approvalFilter !== "all") {
      params.set("approval", approvalFilter);
    }
    if (positionFilter !== "all") {
      params.set("position", positionFilter);
    }
    if (provinceFilter !== "all") {
      params.set("province", provinceFilter);
    }
    if (page > 1) {
      params.set("page", String(page));
    }
    setSearchParams(params, { replace: true });
  }, [
    query,
    healthServiceCodeQuery,
    statusFilter,
    approvalFilter,
    positionFilter,
    provinceFilter,
    page,
    setSearchParams,
  ]);

  const detailQuerySuffix = useMemo(() => {
    const params = new URLSearchParams();
    if (query) {
      params.set("q", query);
    }
    if (healthServiceCodeQuery) {
      params.set("hsc", healthServiceCodeQuery);
    }
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (approvalFilter !== "all") {
      params.set("approval", approvalFilter);
    }
    if (positionFilter !== "all") {
      params.set("position", positionFilter);
    }
    if (provinceFilter !== "all") {
      params.set("province", provinceFilter);
    }
    if (page > 1) {
      params.set("page", String(page));
    }
    const serialized = params.toString();
    return serialized ? `?${serialized}` : "";
  }, [
    query,
    healthServiceCodeQuery,
    statusFilter,
    approvalFilter,
    positionFilter,
    provinceFilter,
    page,
  ]);

  useEffect(() => {
    const requestKey = JSON.stringify({
      query,
      healthServiceCodeQuery,
      refreshToken,
      statusFilter,
      approvalFilter,
      positionFilter,
      provinceFilter,
      page,
    });
    let isCurrent = true;

    setLoading(true);
    setError(null);

    const runRequest = () => {
      if (pendingRequestRef.current?.key === requestKey) {
        return pendingRequestRef.current.promise;
      }

      const params: OfficerQueryParams = {
        search: query || undefined,
        health_service_id: healthServiceCodeQuery || undefined,
        limit: DEFAULT_PAGE_SIZE,
        page,
      };
      if (statusFilter === "active") {
        params.is_active = true;
      } else if (statusFilter === "inactive") {
        params.is_active = false;
      }
      if (approvalFilter !== "all") {
        params.approval_status = approvalFilter;
      }
      if (positionFilter !== "all") {
        params.position_id = positionFilter;
      }
      if (provinceFilter !== "all") {
        params.province_id = provinceFilter;
      }

      const promise = listOfficers(params);
      pendingRequestRef.current = { key: requestKey, promise };
      promise.finally(() => {
        if (pendingRequestRef.current?.key === requestKey) {
          pendingRequestRef.current = null;
        }
      });
      return promise;
    };

    runRequest()
      .then((response) => {
        if (!isCurrent) {
          return;
        }
        const { items, pagination } = response;
        const resolvedPages =
          pagination.total === 0 ? 1 : Math.max(1, pagination.pages || 1);
        if (
          (pagination.total > 0 && page > resolvedPages) ||
          (pagination.total === 0 && page !== 1)
        ) {
          setPage(pagination.total === 0 ? 1 : resolvedPages);
          return;
        }
        setOfficers(items);
        setTotalPages(resolvedPages);
        setTotalCount(pagination.total);
      })
      .catch(() => {
        if (!isCurrent) {
          return;
        }
        setError("ไม่สามารถโหลดรายชื่อเจ้าหน้าที่ได้ กรุณาลองใหม่อีกครั้ง");
        setTotalPages(1);
        setTotalCount(0);
      })
      .finally(() => {
        if (!isCurrent) {
          return;
        }
        setLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [
    query,
    healthServiceCodeQuery,
    refreshToken,
    statusFilter,
    approvalFilter,
    positionFilter,
    provinceFilter,
    page,
  ]);

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(1);
    setQuery(searchTerm.trim());
    setHealthServiceCodeQuery(healthServiceCodeTerm.trim());
  };

  const handleRefresh = () => setRefreshToken((token: number) => token + 1);

  const requestToggleActive = (officer: OfficerListItem) => {
    if (busyOfficerId) {
      return;
    }
    if (officer.permissions && !officer.permissions.can_toggle_active) {
      return;
    }
    setConfirmState({ type: "toggle", officer });
  };

  const requestApprove = (officer: OfficerListItem) => {
    if (busyOfficerId) {
      return;
    }
    if (officer.permissions && !officer.permissions.can_approve) {
      return;
    }
    setConfirmState({ type: "approve", officer });
  };

  const requestReject = (officer: OfficerListItem) => {
    if (busyOfficerId) {
      return;
    }
    if (officer.permissions && !officer.permissions.can_approve) {
      return;
    }
    setConfirmState({ type: "reject", officer });
  };

  const resetConfirmation = () => {
    if (actionBusy) {
      return;
    }
    setConfirmState(null);
  };

  const handleConfirmAction = async () => {
    if (!confirmState) {
      return;
    }

    const { type, officer } = confirmState;
    setActionBusy(true);
    setBusyOfficerId(officer.id);
    setError(null);

    try {
      if (type === "toggle") {
        await setOfficerActiveStatus(officer.id, !officer.is_active);
      } else if (type === "approve") {
        await approveOfficer(officer.id);
      } else if (type === "reject") {
        await rejectOfficer(officer.id);
      }
      setConfirmState(null);
      handleRefresh();
    } catch (err) {
      if (type === "toggle") {
        setError("ไม่สามารถเปลี่ยนสถานะได้ กรุณาลองใหม่");
      } else if (type === "approve") {
        setError("ไม่สามารถอนุมัติคำขอได้ กรุณาลองใหม่");
      } else if (type === "reject") {
        setError("ไม่สามารถปฏิเสธคำขอได้ กรุณาลองใหม่");
      }
    } finally {
      setActionBusy(false);
      setBusyOfficerId(null);
    }
  };

  const rows = useMemo(() => officers, [officers]);

  const confirmTitle = (() => {
    if (!confirmState) {
      return "";
    }
    switch (confirmState.type) {
      case "toggle":
        return "ยืนยันการเปลี่ยนสถานะ";
      case "approve":
        return "ยืนยันการอนุมัติ";
      case "reject":
        return "ยืนยันการปฏิเสธ";
      default:
        return "";
    }
  })();

  const confirmMessage = (() => {
    if (!confirmState) {
      return "";
    }
    const { officer, type } = confirmState;
    if (type === "toggle") {
      return `ต้องการ${
        officer.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"
      }บัญชีของ ${officer.first_name} ${
        officer.last_name
      } หรือไม่?\nคุณสามารถปรับสถานะได้อีกครั้งหลังจากยืนยัน`;
    }
    if (type === "approve") {
      return `ต้องการอนุมัติคำขอของ ${officer.first_name} ${officer.last_name} หรือไม่?\nระบบจะเปิดใช้งานบัญชีให้ทันที`;
    }
    if (type === "reject") {
      return `ต้องการปฏิเสธคำขอของ ${officer.first_name} ${officer.last_name} หรือไม่?\nผู้สมัครจะไม่สามารถเข้าระบบได้จนกว่าจะสมัครใหม่`;
    }
    return "";
  })();

  const handleApprovalFilterChange = (value: ApprovalFilter) => {
    if (approvalFilter === value) {
      return;
    }
    setApprovalFilter(value);
    setPage(1);
  };

  const handleStatusFilterChange = (value: StatusFilter) => {
    if (statusFilter === value) {
      return;
    }
    setStatusFilter(value);
    setPage(1);
  };

  const handleProvinceFilterChange = (value: string) => {
    if (isProvinceFilterLocked) {
      return;
    }
    if (provinceFilter === value) {
      return;
    }
    setProvinceFilter(value);
    setPage(1);
  };

  const handleResetFilters = () => {
    setStatusFilter("all");
    setApprovalFilter("all");
    setPositionFilter("all");
    setProvinceFilter(
      isProvinceFilterLocked && enforcedProvinceFilter
        ? enforcedProvinceFilter
        : "all",
    );
    setSearchTerm("");
    setHealthServiceCodeTerm("");
    setQuery("");
    setHealthServiceCodeQuery("");
    setPage(1);
  };

  const handlePageChange = (nextPage: number) => {
    if (loading) {
      return;
    }
    if (nextPage < 1 || nextPage > totalPages || nextPage === page) {
      return;
    }
    setPage(nextPage);
  };

  const firstItemIndex =
    totalCount === 0 ? 0 : (page - 1) * DEFAULT_PAGE_SIZE + 1;
  const lastItemIndex =
    totalCount === 0 ? 0 : firstItemIndex + officers.length - 1;

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 rounded-2xl bg-gradient-to-r from-blue-600 via-blue-500 to-sky-500 p-6 text-white shadow-lg">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-white/80">
              Officer Directory
            </p>
            <h1 className="text-2xl font-bold">จัดการเจ้าหน้าที่</h1>
            <p className="text-sm text-white/80">
              ค้นหา เพิ่ม แก้ไข และเปลี่ยนสถานะของบัญชีเจ้าหน้าที่ในระบบ
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-blue-600 shadow-sm transition hover:bg-slate-100"
              to="/officers/create"
            >
              + เพิ่มเจ้าหน้าที่
            </Link>
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading}
              className="rounded-lg border border-white/40 px-4 py-2 text-sm font-semibold text-white transition hover:border-white hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-70"
            >
              รีเฟรช
            </button>
          </div>
        </div>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <form
          className="flex flex-col gap-3 sm:flex-row"
          onSubmit={handleSearchSubmit}
        >
          <div className="relative flex-1">
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="ค้นหาโดยชื่อ นามสกุล เลขบัตร หรือหน่วยบริการสุขภาพ"
              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 pr-10 text-sm font-medium text-slate-700 shadow-inner transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m21 21-4.35-4.35m0 0A7.5 7.5 0 1 0 8.5 15.5a7.5 7.5 0 0 0 8.15 1.15Z"
                />
              </svg>
            </span>
          </div>
          <div className="relative sm:w-64">
            <input
              value={healthServiceCodeTerm}
              onChange={(event) => setHealthServiceCodeTerm(event.target.value)}
              placeholder="รหัสหน่วยบริการสุขภาพ"
              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm font-medium text-slate-700 shadow-inner transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-11 items-center justify-center rounded-xl bg-blue-600 px-6 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            ค้นหา
          </button>
        </form>

        <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <label
                className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                htmlFor="status-filter"
              >
                สถานะ
              </label>
              <div className="relative">
                <select
                  id="status-filter"
                  value={statusFilter}
                  onChange={(event) =>
                    handleStatusFilterChange(event.target.value as StatusFilter)
                  }
                  className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {STATUS_FILTER_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <label
                className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                htmlFor="approval-filter"
              >
                การอนุมัติ
              </label>
              <div className="relative">
                <select
                  id="approval-filter"
                  value={approvalFilter}
                  onChange={(event) =>
                    handleApprovalFilterChange(
                      event.target.value as ApprovalFilter,
                    )
                  }
                  className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {APPROVAL_FILTER_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <label
                className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                htmlFor="position-filter"
              >
                ตำแหน่ง
              </label>
              <div className="relative">
                <select
                  id="position-filter"
                  value={positionFilter}
                  onChange={(event) => {
                    setPositionFilter(event.target.value);
                    setPage(1);
                  }}
                  className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  <option value="all">ทุกตำแหน่ง</option>
                  {filteredPositions.map((position) => (
                    <option key={position.id} value={position.id}>
                      {position.name_th ?? position.label ?? position.id}
                    </option>
                  ))}
                </select>
                {loadingPositions && (
                  <span className="pointer-events-none absolute inset-y-0 right-3 inline-flex items-center text-slate-400">
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 0 1 8-8v4l3.536-3.536A8 8 0 1 1 4 12Z"
                      />
                    </svg>
                  </span>
                )}
                {!loadingPositions && positionsError && (
                  <p className="mt-1 text-[11px] font-medium text-rose-500">
                    {positionsError}
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <label
                className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                htmlFor="province-filter"
              >
                จังหวัด
              </label>
              <div className="relative">
                <select
                  id="province-filter"
                  value={provinceFilter}
                  onChange={(event) =>
                    handleProvinceFilterChange(event.target.value)
                  }
                  disabled={isProvinceFilterLocked}
                  className={`h-10 w-full rounded-xl border bg-white px-3 text-sm font-medium text-slate-700 shadow-sm transition focus:outline-none focus:ring-2 focus:ring-blue-200 ${
                    isProvinceFilterLocked
                      ? "border-slate-200 text-slate-500"
                      : "border-slate-200 focus:border-blue-500 focus:ring-blue-200"
                  }`}
                >
                  {!isProvinceFilterLocked && (
                    <option value="all">ทุกจังหวัด</option>
                  )}
                  {provinceOptions.map((province) => (
                    <option key={province.id} value={province.id}>
                      {province.label}
                    </option>
                  ))}
                </select>
                {loadingProvinces && (
                  <span className="pointer-events-none absolute inset-y-0 right-3 inline-flex items-center text-slate-400">
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 0 1 8-8v4l3.536-3.536A8 8 0 1 1 4 12Z"
                      />
                    </svg>
                  </span>
                )}
                {!loadingProvinces && provincesError && (
                  <p className="mt-1 text-[11px] font-medium text-rose-500">
                    {provincesError}
                  </p>
                )}
                {isProvinceFilterLocked ? (
                  <p className="mt-1 text-[11px] text-slate-400">
                    ระบบล็อกจังหวัดตามสิทธิ์ของคุณ
                  </p>
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleResetFilters}
              className="inline-flex h-10 items-center rounded-xl border border-slate-200 px-4 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
            >
              เคลียร์
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-inner">
            {error}
          </div>
        )}

        {loading ? (
          <div className="mt-10">
            <PageLoader />
          </div>
        ) : (
          <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    ชื่อ-นามสกุล
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    ตำแหน่ง
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    รหัสหน่วยบริการ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    หน่วยบริการสุขภาพ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    จังหวัด
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    อำเภอ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    สถานะ
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    การอนุมัติ
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                    การจัดการ
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {rows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={9}
                      className="px-4 py-6 text-center text-sm text-slate-500"
                    >
                      ไม่พบข้อมูลเจ้าหน้าที่
                    </td>
                  </tr>
                ) : (
                  rows.map((officer) => (
                    <tr
                      key={officer.id}
                      className="transition hover:bg-slate-50"
                    >
                      <td className="px-4 py-4">
                        <Link
                          to={`/officers/${officer.id}${detailQuerySuffix}`}
                          className="text-sm font-semibold text-slate-900 transition hover:text-blue-600"
                        >
                          {officer.first_name} {officer.last_name}
                        </Link>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500">
                          <span>เลขบัตร</span>
                          <SensitiveValue
                            value={officer.citizen_id}
                            className="inline-flex items-center gap-1"
                            valueClassName="font-mono text-xs text-slate-600"
                            buttonClassName="rounded-full border border-slate-200 p-1 text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
                            revealIcon={<EyeIcon />}
                            hideIcon={<EyeOffIcon />}
                          />
                        </div>
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">
                        {officer.position_name_th ?? "-"}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700 font-mono">
                        {officer.health_service_id ?? "-"}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">
                        {officer.health_service_name_th ?? "-"}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">
                        {officer.province_name_th ?? "-"}
                      </td>
                      <td className="px-4 py-4 text-sm text-slate-700">
                        {officer.district_name_th ?? "-"}
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex min-w-[104px] items-center justify-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                            officer.is_active
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-rose-100 text-rose-700"
                          }`}
                        >
                          {officer.is_active ? "เปิดใช้งาน" : "ปิดใช้งาน"}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span
                          className={`inline-flex min-w-[104px] items-center justify-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                            APPROVAL_STATUS_BADGE_CLASSES[
                              officer.approval_status
                            ]
                          }`}
                        >
                          {APPROVAL_STATUS_LABELS[officer.approval_status]}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          <IconActionLink
                            label="ดูรายละเอียด"
                            to={`/officers/${officer.id}${detailQuerySuffix}`}
                            tone="info"
                          >
                            <EyeIcon className="h-4 w-4" />
                          </IconActionLink>
                          {officer.approval_status === "pending" &&
                            (officer.permissions?.can_approve ?? true) && (
                              <>
                                <IconButton
                                  label="อนุมัติคำขอ"
                                  onClick={() => requestApprove(officer)}
                                  disabled={busyOfficerId === officer.id}
                                  tone="success"
                                  busy={
                                    busyOfficerId === officer.id && actionBusy
                                  }
                                >
                                  <IconCheck />
                                </IconButton>
                                <IconButton
                                  label="ปฏิเสธคำขอ"
                                  onClick={() => requestReject(officer)}
                                  disabled={busyOfficerId === officer.id}
                                  tone="warning"
                                  busy={
                                    busyOfficerId === officer.id && actionBusy
                                  }
                                >
                                  <IconX />
                                </IconButton>
                              </>
                            )}
                          {(officer.permissions?.can_toggle_active ?? true) &&
                            officer.approval_status === "approved" && (
                              <IconButton
                                label={
                                  officer.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"
                                }
                                onClick={() => requestToggleActive(officer)}
                                disabled={busyOfficerId === officer.id}
                                tone={officer.is_active ? "danger" : "success"}
                                busy={
                                  busyOfficerId === officer.id && actionBusy
                                }
                              >
                                <IconPower />
                              </IconButton>
                            )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        {!loading && (
          <div className="mt-6 flex flex-col items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-600 shadow-sm sm:flex-row sm:text-sm">
            <div>
              {totalCount > 0
                ? `แสดง ${firstItemIndex.toLocaleString()} - ${lastItemIndex.toLocaleString()} จาก ${totalCount.toLocaleString()} รายการ`
                : "ไม่มีข้อมูลเจ้าหน้าที่"}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handlePageChange(page - 1)}
                disabled={loading || page <= 1}
                className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                ก่อนหน้า
              </button>
              <span className="min-w-[72px] text-center font-semibold text-slate-700">
                หน้า {totalPages === 0 ? 0 : page} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => handlePageChange(page + 1)}
                disabled={loading || page >= totalPages || totalPages === 0}
                className="inline-flex items-center justify-center rounded-lg border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                ถัดไป
              </button>
            </div>
          </div>
        )}
        <ConfirmDialog
          open={Boolean(confirmState)}
          title={confirmTitle}
          message={confirmMessage}
          onCancel={resetConfirmation}
          onConfirm={handleConfirmAction}
          confirmLabel={(() => {
            if (!confirmState) {
              return "ยืนยัน";
            }
            if (confirmState.type === "toggle") {
              return confirmState.officer.is_active
                ? "ปิดใช้งาน"
                : "เปิดใช้งาน";
            }
            if (confirmState.type === "approve") {
              return "อนุมัติ";
            }
            if (confirmState.type === "reject") {
              return "ปฏิเสธ";
            }
            return "ยืนยัน";
          })()}
          variant={confirmState?.type === "reject" ? "danger" : "default"}
          busy={actionBusy}
        />
      </section>
    </div>
  );
};

export default OfficersListPage;
