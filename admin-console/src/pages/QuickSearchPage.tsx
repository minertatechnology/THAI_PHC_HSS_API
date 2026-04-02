import React, { FormEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { searchClientBlockCandidates } from "../api/oauthClients";
import { fetchOfficerDisplayNameById, resetOsmPassword, resetPeoplePassword, resetYuwaPassword, resetGenHPassword, setOsmActiveStatus, setPeopleActiveStatus, setYuwaActiveStatus, setGenHActiveStatus } from "../api/officers";
import { fetchOsmDetail, fetchYuwaOsmDetail } from "../api/osm";
import { fetchPeopleDetail } from "../api/people";
import { fetchGenHDetail } from "../api/genH";
import { ClientBlockCandidate, UserType } from "../types/oauthClient";
import { SensitiveValue } from "../components/ui/SensitiveValue";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { useAuthContext } from "../context/AuthContext";
import type { PermissionScope } from "../types/auth";
import type { AdministrativeLevel, OfficerPasswordResetResult } from "../types/officer";
import type { OsmProfileDetail } from "../types/osm";
import type { YuwaOsmDetail } from "../types/yuwaOsm";
import type { PeopleDetail } from "../types/people";
import type { GenHDetail } from "../types/genH";

const DEFAULT_LIMIT = 50;

type IconProps = { className?: string };

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

const IconKey = ({ className = "h-5 w-5" }: IconProps) => (
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
    <circle cx="7.5" cy="12.5" r="4" />
    <path d="M11 12.5h10" />
    <path d="M17 12.5v4" />
  </svg>
);

const IconInfo = ({ className = "h-5 w-5" }: IconProps) => (
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
    <circle cx="12" cy="12" r="9" />
    <path d="M12 16v-4" />
    <path d="M12 8h.01" />
  </svg>
);

const IconSpinner = ({ className = "h-5 w-5" }: IconProps) => (
  <svg viewBox="0 0 24 24" aria-hidden="true" className={`${className} animate-spin`} fill="none">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth={2} strokeOpacity={0.2} />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
  </svg>
);

type IconButtonTone = "neutral" | "info" | "success" | "warning" | "danger";

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
  const baseClass =
    "inline-flex h-9 w-9 items-center justify-center rounded-lg border text-sm transition focus:outline-none focus:ring-2 focus:ring-blue-100 focus:ring-offset-1";
  const toneClass: Record<IconButtonTone, string> = {
    neutral: "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-100",
    info: "border-blue-200 bg-blue-50 text-blue-600 hover:border-blue-300 hover:bg-blue-100",
    success: "border-emerald-200 bg-emerald-50 text-emerald-600 hover:border-emerald-300 hover:bg-emerald-100",
    warning: "border-amber-200 bg-amber-50 text-amber-600 hover:border-amber-300 hover:bg-amber-100",
    danger: "border-rose-200 bg-rose-50 text-rose-600 hover:border-rose-300 hover:bg-rose-100",
  };
  const disabledClass = disabled ? "cursor-not-allowed opacity-50" : "";

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`${baseClass} ${toneClass[tone]} ${disabledClass}`.trim()}
      disabled={disabled}
    >
      {busy ? <IconSpinner className="h-4 w-4" /> : children}
      <span className="sr-only">{label}</span>
    </button>
  );
};

type DetailPayload =
  | { kind: "osm"; data: OsmProfileDetail }
  | { kind: "yuwa_osm"; data: YuwaOsmDetail }
  | { kind: "people"; data: PeopleDetail }
  | { kind: "gen_h"; data: GenHDetail }
  | { kind: "candidate"; data: ClientBlockCandidate };

type DetailField = {
  label: string;
  value?: React.ReactNode;
};

const DetailSection: React.FC<{ title: string; fields: DetailField[] }> = ({ title, fields }) => (
  <section>
    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
    <dl className="mt-2 grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
      {fields.map((field) => (
        <div key={field.label} className="flex flex-col">
          <dt className="text-[11px] font-semibold text-slate-400">{field.label}</dt>
          <dd className="text-sm text-slate-700">{field.value ?? <span className="text-slate-400">-</span>}</dd>
        </div>
      ))}
    </dl>
  </section>
);

type DetailDialogProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  busy?: boolean;
  error?: string | null;
  children?: React.ReactNode;
  disableDismiss?: boolean;
  dimmed?: boolean;
};

const DetailDialog: React.FC<DetailDialogProps> = ({ open, title, onClose, busy = false, error, children, disableDismiss = false, dimmed = false }) => {
  if (!open) {
    return null;
  }

  const handleBackdropClick = () => {
    if (!disableDismiss) {
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4 py-8" onClick={handleBackdropClick}>
      <div
        className={`relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-2xl shadow-2xl ${dimmed ? "bg-slate-50" : "bg-white"}`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            disabled={disableDismiss}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 text-slate-500 transition hover:border-slate-300 hover:bg-slate-100 disabled:cursor-not-allowed"
          >
            <span className="text-lg leading-none">×</span>
            <span className="sr-only">ปิด</span>
          </button>
        </div>
        {busy ? (
          <div className="flex flex-col items-center justify-center gap-3 px-6 py-16 text-slate-500">
            <IconSpinner className="h-8 w-8" />
            <span className="text-sm font-medium">กำลังดึงรายละเอียด</span>
          </div>
        ) : (
          <div className="overflow-y-auto px-6 py-6">
            {error ? (
              <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 shadow-inner">
                {error}
              </div>
            ) : null}
            {children}
          </div>
        )}
      </div>
    </div>
  );
};

export interface QuickSearchPageProps {
  userType: Extract<UserType, "osm" | "yuwa_osm" | "people" | "gen_h">;
  title: string;
  subtitle?: string;
  description: string;
  placeholder?: string;
  helperText?: string;
  limit?: number;
  introHighlights?: { label: string; detail: string }[];
  headerActions?: ReactNode;
}

export const QuickSearchPage: React.FC<QuickSearchPageProps> = ({
  userType,
  title,
  subtitle,
  description,
  placeholder = "พิมพ์คำค้นหา",
  helperText,
  limit = DEFAULT_LIMIT,
  introHighlights,
  headerActions
}: QuickSearchPageProps) => {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [results, setResults] = useState<ClientBlockCandidate[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [offset, setOffset] = useState<number>(0);
  const [total, setTotal] = useState<number>(0);
  const resultsPanelRef = useRef<HTMLDivElement>(null);
  const [resetTarget, setResetTarget] = useState<ClientBlockCandidate | null>(null);
  const [resetBusy, setResetBusy] = useState<boolean>(false);
  const [resetError, setResetError] = useState<string | null>(null);
  const [statusBusyId, setStatusBusyId] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [temporaryReset, setTemporaryReset] = useState<{ password: string; name: string; userType: ClientBlockCandidate["user_type"] } | null>(null);
  const [copiedTempPassword, setCopiedTempPassword] = useState<boolean>(false);
  const [detailTarget, setDetailTarget] = useState<ClientBlockCandidate | null>(null);
  const [detailPayload, setDetailPayload] = useState<DetailPayload | null>(null);
  const [detailBusy, setDetailBusy] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [actorNameMap, setActorNameMap] = useState<Record<string, string>>({});

  const isLikelyUuid = useCallback((value?: string | null): value is string => {
    if (!value) {
      return false;
    }
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.trim());
  }, []);

  const getActorDisplay = useCallback(
    (value?: string | null) => {
      if (!value) {
        return "-";
      }
      if (!isLikelyUuid(value)) {
        const normalized = `${value}`.trim();
        return normalized.length > 0 ? normalized : "-";
      }
      return actorNameMap[value] ?? "-";
    },
    [actorNameMap, isLikelyUuid]
  );

  useEffect(() => {
    setResults([]);
    setQuery("");
    setHasSearched(false);
    setError(null);
    setResetError(null);
    setStatusError(null);
    setStatusNotice(null);
    setStatusBusyId(null);
    setTemporaryReset(null);
    setCopiedTempPassword(false);
    setDetailTarget(null);
    setDetailPayload(null);
    setDetailError(null);
    setDetailBusy(false);
    setOffset(0);
    setTotal(0);
  }, [userType]);

  useEffect(() => {
    const ids = new Set<string>();

    if (detailPayload?.kind === "osm") {
      const detail = detailPayload.data;
      [detail.approval_by, detail.created_by, detail.updated_by].forEach((value) => {
        if (isLikelyUuid(value) && !actorNameMap[value]) {
          ids.add(value);
        }
      });
    }

    if (detailPayload?.kind === "yuwa_osm") {
      const detail = detailPayload.data;
      [detail.approved_by, detail.rejected_by].forEach((value) => {
        if (isLikelyUuid(value) && !actorNameMap[value]) {
          ids.add(value);
        }
      });
    }

    if (detailPayload?.kind === "people") {
      const detail = detailPayload.data;
      if (isLikelyUuid(detail.transferred_by) && !actorNameMap[detail.transferred_by]) {
        ids.add(detail.transferred_by);
      }
    }

    if (detailPayload?.kind === "candidate") {
      const detail = detailPayload.data;
      if (isLikelyUuid(detail.transferred_by) && !actorNameMap[detail.transferred_by]) {
        ids.add(detail.transferred_by);
      }
    }

    if (ids.size === 0) {
      return;
    }

    let cancelled = false;
    const run = async () => {
      const pairs = await Promise.all(
        Array.from(ids).map(async (id) => {
          try {
            const name = await fetchOfficerDisplayNameById(id);
            return [id, name] as const;
          } catch {
            return [id, null] as const;
          }
        })
      );

      if (cancelled) {
        return;
      }

      setActorNameMap((prev) => {
        const next = { ...prev };
        pairs.forEach(([id, name]) => {
          if (name) {
            next[id] = name;
          }
        });
        return next;
      });
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [detailPayload, actorNameMap, isLikelyUuid]);

  useEffect(() => {
    if (!query) {
      setResults([]);
      setError(null);
      setLoading(false);
      setTotal(0);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setStatusNotice(null);
    setStatusError(null);

    searchClientBlockCandidates({ userType, query, limit, offset })
      .then((data) => {
        if (!cancelled) {
          setResults(data.items);
          setTotal(data.total);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("ไม่สามารถค้นหาข้อมูลได้ กรุณาลองใหม่อีกครั้ง");
          setResults([]);
          setTotal(0);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [query, userType, limit, offset]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = searchTerm.trim();
    if (!trimmed) {
      setQuery("");
      setHasSearched(false);
      setResults([]);
      setOffset(0);
      setTotal(0);
      return;
    }
    setOffset(0);
    setQuery(trimmed);
    setHasSearched(true);
  };

  const displayedResults = useMemo(() => results, [results]);

  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  const scrollToResults = useCallback(() => {
    resultsPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const handlePrevPage = useCallback(() => {
    setOffset((prev) => Math.max(0, prev - limit));
    scrollToResults();
  }, [limit, scrollToResults]);

  const handleNextPage = useCallback(() => {
    setOffset((prev) => prev + limit);
    scrollToResults();
  }, [limit, scrollToResults]);

  const handleGoToPage = useCallback(
    (page: number) => {
      const clamped = Math.max(1, Math.min(page, totalPages));
      setOffset((clamped - 1) * limit);
      scrollToResults();
    },
    [limit, totalPages, scrollToResults]
  );

  const { user } = useAuthContext();
  const permissionScope: PermissionScope | null | undefined = user?.permission_scope;
  const manageableLevels = permissionScope?.manageable_levels ?? [];
  const hasCommunityScope = Boolean(permissionScope && manageableLevels.length > 0);

  const typeLabels: Record<Extract<UserType, "osm" | "yuwa_osm" | "people" | "gen_h">, string> = {
    osm: "อสม.",
    yuwa_osm: "ยุวอสม.",
    people: "ประชาชน",
    gen_h: "GenH",
  };

  const typeBadgeClasses: Record<Extract<UserType, "osm" | "yuwa_osm" | "people" | "gen_h">, string> = {
    osm: "bg-emerald-100 text-emerald-700",
    yuwa_osm: "bg-teal-100 text-teal-700",
    people: "bg-sky-100 text-sky-700",
    gen_h: "bg-amber-100 text-amber-700",
  };

  const resolveCommunityType = (value: UserType): Extract<UserType, "osm" | "yuwa_osm" | "people" | "gen_h"> =>
    value === "yuwa_osm" ? "yuwa_osm" : value === "people" ? "people" : value === "gen_h" ? "gen_h" : "osm";

  const currentTypeLabel = typeLabels[userType];

  const resultSummary = useMemo(() => {
    if (loading) {
      return "กำลังค้นหา";
    }
    if (!hasSearched) {
      return "รอคำค้น";
    }
    const suffix = currentTypeLabel ? ` (${currentTypeLabel})` : "";
    if (total > 0) {
      const from = offset + 1;
      const to = Math.min(offset + limit, total);
      return `แสดง ${from}-${to} จาก ${total} รายการ${suffix}`;
    }
    return displayedResults.length > 0 ? `พบ ${displayedResults.length} รายการ${suffix}` : "ไม่พบข้อมูล";
  }, [displayedResults.length, hasSearched, loading, currentTypeLabel, total, offset, limit]);

  const mapResetErrorDetail = useCallback((detail?: string | null) => {
    if (!detail) {
      return null;
    }
    if (detail === "insufficient_scope" || detail === "forbidden") {
      return "คุณไม่มีสิทธิ์จัดการบัญชีนี้";
    }
    if (detail === "insufficient_scope_self_action") {
      return "ไม่สามารถรีเซ็ตรหัสผ่านบัญชีของตนเองได้";
    }
    if (detail === "status_update_failed") {
      return "ไม่สามารถอัปเดตสถานะได้ กรุณาลองใหม่";
    }
    if (detail === "people_already_transferred") {
      return "บัญชีนี้ถูกย้ายไป ยุวอสม. แล้ว ไม่สามารถเปิดใช้งานกลับได้";
    }
    if (detail === "gen_h_already_transferred") {
      return "บัญชีนี้ถูกย้ายไป ประชาชน แล้ว ไม่สามารถเปิดใช้งานกลับได้";
    }
    if (detail === "password_reset_failed") {
      return "ไม่สามารถรีเซ็ตรหัสผ่านได้ กรุณาลองใหม่";
    }
    if (detail === "people_user_not_found" || detail === "gen_h_user_not_found") {
      return "ไม่พบบัญชีที่ต้องการจัดการ";
    }
    if (detail === "osm_not_found" || detail === "yuwa_osm_user_not_found" || detail === "people_user_not_found") {
      return "ไม่พบบัญชีที่ต้องการจัดการ";
    }
    return null;
  }, []);

  const mapDetailErrorMessage = useCallback((detail?: string | null) => {
    if (!detail) {
      return "ไม่สามารถโหลดรายละเอียดได้ กรุณาลองใหม่";
    }
    if (detail === "osm_not_found" || detail === "yuwa_osm_user_not_found" || detail === "people_user_not_found" || detail === "gen_h_user_not_found") {
      return "ไม่พบข้อมูลรายละเอียดของบัญชีนี้";
    }
    if (detail === "insufficient_scope" || detail === "insufficient_scope_view_record" || detail === "insufficient_scope_department_required") {
      return "คุณไม่มีสิทธิ์ดูรายละเอียดของบัญชีนี้";
    }
    return "ไม่สามารถโหลดรายละเอียดได้ กรุณาลองใหม่";
  }, []);

  useEffect(() => {
    if (!detailTarget) {
      setDetailPayload(null);
      setDetailError(null);
      setDetailBusy(false);
      return;
    }

    let cancelled = false;
    setDetailBusy(true);
    setDetailError(null);
    setDetailPayload(null);

    const resolveDetail = async () => {
      try {
        if (detailTarget.user_type === "osm") {
          const detail = await fetchOsmDetail(detailTarget.user_id);
          if (!cancelled) {
            setDetailPayload({ kind: "osm", data: detail });
          }
        } else if (detailTarget.user_type === "yuwa_osm") {
          const detail = await fetchYuwaOsmDetail(detailTarget.user_id);
          if (!cancelled) {
            setDetailPayload({ kind: "yuwa_osm", data: detail });
          }
        } else if (detailTarget.user_type === "people") {
          const detail = await fetchPeopleDetail(detailTarget.user_id);
          if (!cancelled) {
            setDetailPayload({ kind: "people", data: detail });
          }
        } else if (detailTarget.user_type === "gen_h") {
          const detail = await fetchGenHDetail(detailTarget.user_id);
          if (!cancelled) {
            setDetailPayload({ kind: "gen_h", data: detail });
          }
        } else if (!cancelled) {
          setDetailPayload({ kind: "candidate", data: detailTarget });
        }
      } catch (err: any) {
        if (cancelled) {
          return;
        }
        const detailCode = err?.response?.data?.detail;
        setDetailError(mapDetailErrorMessage(detailCode));
        setDetailPayload({ kind: "candidate", data: detailTarget });
      } finally {
        if (!cancelled) {
          setDetailBusy(false);
        }
      }
    };

    void resolveDetail();

    return () => {
      cancelled = true;
    };
  }, [detailTarget, mapDetailErrorMessage]);

  const canManageCandidate = useCallback(
    (candidate: ClientBlockCandidate): boolean => {
      if (!permissionScope || !hasCommunityScope) {
        return false;
      }
      if (candidate.user_type !== "osm" && candidate.user_type !== "yuwa_osm" && candidate.user_type !== "people") {
        return false;
      }

      const candidateLevel: AdministrativeLevel | "country" = candidate.village_code
        ? "village"
        : candidate.subdistrict_code
          ? "subdistrict"
          : candidate.district_code
            ? "district"
            : candidate.province_code
              ? "province"
              : "country";

      if (manageableLevels.length > 0 && !manageableLevels.includes(candidateLevel as AdministrativeLevel)) {
        return false;
      }

      const matches = (scopeCode?: string | null, targetCode?: string | null) => {
        if (!scopeCode) {
          return true;
        }
        if (!targetCode) {
          return true;
        }
        return scopeCode === targetCode;
      };

      const codes = permissionScope.codes ?? {};
      const viewerLevel = permissionScope.level;

      if (viewerLevel === "country") {
        return true;
      }
      if (viewerLevel === "region") {
        return matches(codes.region_code, candidate.region_code);
      }
      if (viewerLevel === "area") {
        return matches(codes.health_area_id, candidate.health_area_code);
      }
      if (viewerLevel === "province") {
        return matches(codes.province_id, candidate.province_code);
      }
      if (viewerLevel === "district") {
        return (
          matches(codes.province_id, candidate.province_code) && matches(codes.district_id, candidate.district_code)
        );
      }
      if (viewerLevel === "subdistrict") {
        return (
          matches(codes.province_id, candidate.province_code) &&
          matches(codes.district_id, candidate.district_code) &&
          matches(codes.subdistrict_id, candidate.subdistrict_code)
        );
      }
      if (viewerLevel === "village") {
        return (
          matches(codes.province_id, candidate.province_code) &&
          matches(codes.district_id, candidate.district_code) &&
          matches(codes.subdistrict_id, candidate.subdistrict_code) &&
          matches(codes.village_code, candidate.village_code)
        );
      }
      return false;
    },
    [permissionScope, manageableLevels, hasCommunityScope]
  );

  const handleOpenReset = (candidate: ClientBlockCandidate) => {
    setResetTarget(candidate);
    setResetError(null);
    setStatusError(null);
    setStatusNotice(null);
    setCopiedTempPassword(false);
  };

  const handleCloseReset = () => {
    if (resetBusy) {
      return;
    }
    setResetTarget(null);
  };

  const handleOpenDetails = useCallback((candidate: ClientBlockCandidate) => {
    setDetailTarget(candidate);
  }, []);

  const handleCloseDetails = useCallback(() => {
    setDetailTarget(null);
  }, []);

  useEffect(() => {
    if (!detailTarget) {
      return;
    }

    const listener = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleCloseDetails();
      }
    };

    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, [detailTarget, handleCloseDetails]);

  const handleToggleStatus = async (candidate: ClientBlockCandidate) => {
    const nextState = !candidate.is_active;
    setStatusBusyId(candidate.user_id);
    setStatusError(null);
    setStatusNotice(null);
    try {
      const apiCall = candidate.user_type === "yuwa_osm"
        ? setYuwaActiveStatus
        : candidate.user_type === "people"
          ? setPeopleActiveStatus
          : candidate.user_type === "gen_h"
            ? setGenHActiveStatus
            : setOsmActiveStatus;
      const result = await apiCall(candidate.user_id, nextState);
      const effectiveState = typeof result?.is_active === "boolean" ? result.is_active : nextState;
      setResults((prev) =>
        prev.map((item) =>
          item.user_id === candidate.user_id ? { ...item, is_active: effectiveState } : item
        )
      );
      const communityType = resolveCommunityType(candidate.user_type);
      const label = typeLabels[communityType];
      setStatusNotice(
        `${nextState ? "เปิดใช้งาน" : "ปิดใช้งาน"} ${candidate.full_name || label} (${label}) เรียบร้อย`
      );
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const message = mapResetErrorDetail(detail) ?? "ไม่สามารถอัปเดตสถานะได้ กรุณาลองใหม่";
      setStatusError(message);
    } finally {
      setStatusBusyId(null);
    }
  };

  const handleConfirmReset = async () => {
    if (!resetTarget) {
      return;
    }
    const snapshot = resetTarget;
    setResetBusy(true);
    setResetError(null);
    setCopiedTempPassword(false);
    try {
      const apiCall = snapshot.user_type === "yuwa_osm"
        ? resetYuwaPassword
        : snapshot.user_type === "people"
          ? resetPeoplePassword
          : snapshot.user_type === "gen_h"
            ? resetGenHPassword
            : resetOsmPassword;
      const result: OfficerPasswordResetResult = await apiCall(snapshot.user_id);
      setTemporaryReset({
        password: result.temporary_password,
        name: snapshot.full_name || "ผู้ใช้งาน",
        userType: snapshot.user_type,
      });
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const message = mapResetErrorDetail(detail) ?? "ไม่สามารถรีเซ็ตรหัสผ่านได้ กรุณาลองใหม่";
      setResetError(message);
    } finally {
      setResetBusy(false);
      setResetTarget(null);
    }
  };

  const handleCopyTemporaryPassword = async () => {
    if (!temporaryReset) {
      return;
    }
    try {
      await navigator.clipboard.writeText(temporaryReset.password);
      setCopiedTempPassword(true);
      window.setTimeout(() => setCopiedTempPassword(false), 2000);
    } catch (err) {
      setCopiedTempPassword(false);
    }
  };

  const displayValue = useCallback((value?: string | number | null) => {
    if (value === null || value === undefined) {
      return "-";
    }
    if (typeof value === "number") {
      return Number.isFinite(value) ? value.toString() : "-";
    }
    const text = `${value}`.trim();
    return text || "-";
  }, []);

  const translateGender = useCallback((value?: string | null) => {
    if (!value) {
      return "-";
    }
    const normalized = `${value}`.trim().toLowerCase();
    const labels: Record<string, string> = {
      male: "ชาย",
      female: "หญิง",
      other: "ไม่ระบุ",
    };
    return labels[normalized] ?? value;
  }, []);

  const translateVolunteerStatus = useCallback((value?: string | null) => {
    if (!value) return "-";
    const labels: Record<string, string> = {
      wants_to_be_volunteer: "ต้องการเป็นอาสาสมัคร",
      not_interested: "ไม่ประสงค์เป็นอาสาสมัคร",
      active: "กำลังปฏิบัติหน้าที่",
      inactive: "หยุดปฏิบัติหน้าที่",
    };
    return labels[value.trim().toLowerCase()] ?? value;
  }, []);

  const translateShowbody = useCallback((value?: string | null) => {
    if (!value) return "-";
    const labels: Record<string, string> = {
      "1": "ได้รับเงินค่าป่วยการ",
      "2": "ได้รับเงินค่าป่วยการ",
      "5": "ไม่ขอรับเงินค่าป่วยการ",
      "6": "กลุ่มรอรับเงินค่าป่วยการ",
    };
    return labels[value.trim()] ?? value;
  }, []);

  const translateOsmStatus = useCallback((value?: string | null) => {
    if (value === null || value === undefined || value === "") return "ปกติ";
    const labels: Record<string, string> = {
      "0": "เสียชีวิต",
      "1": "ลาออก",
      "2": "พ้นสภาพ",
    };
    return labels[value.trim()] ?? value;
  }, []);

  const translateMaritalStatus = useCallback((value?: string | null) => {
    if (!value) return "-";
    const labels: Record<string, string> = {
      single: "โสด",
      married: "สมรส",
      divorced: "หย่า",
      widowed: "หม้าย/ร้าง",
      other: "ไม่ระบุ",
    };
    return labels[value.trim().toLowerCase()] ?? value;
  }, []);

  const translateBloodType = useCallback((value?: string | null) => {
    if (!value) return "-";
    const labels: Record<string, string> = {
      A: "A",
      B: "B",
      AB: "AB",
      O: "O",
      other: "ไม่ระบุ",
    };
    return labels[value.trim()] ?? value;
  }, []);

  const formatBirthDateWithAge = useCallback((value?: string | null) => {
    if (!value) return "-";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    const today = new Date();
    let age = today.getFullYear() - parsed.getFullYear();
    const monthDiff = today.getMonth() - parsed.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < parsed.getDate())) {
      age--;
    }
    return `${value} (${age}ปี)`;
  }, []);

  const translateApprovalStatus = useCallback((value?: string | null) => {
    if (!value) return "-";
    const labels: Record<string, string> = {
      approved: "อนุมัติแล้ว",
      pending: "รออนุมัติ",
      rejected: "ปฏิเสธ",
      retired: "พ้นสภาพ",
    };
    return labels[value.trim().toLowerCase()] ?? value;
  }, []);

  const translateScopeLevel = useCallback((value?: string | null) => {
    if (!value) {
      return null;
    }
    const normalized = `${value}`.trim().toLowerCase();
    const labels: Record<string, string> = {
      village: "ระดับหมู่บ้าน",
      subdistrict: "ระดับตำบล",
      district: "ระดับอำเภอ",
      province: "ระดับจังหวัด",
      area: "ระดับเขตสุขภาพ",
      region: "ระดับภูมิภาค",
      country: "ระดับกรม",
    };
    return labels[normalized] ?? value;
  }, []);

  const describeActor = useCallback(
    (name?: string | null, position?: string | null, scopeLabel?: string | null, scopeLevel?: string | null) => {
      const effectiveScope = scopeLabel ?? translateScopeLevel(scopeLevel);
      const metaParts = [position, effectiveScope].filter((part): part is string => Boolean(part && part.trim().length > 0));
      const meta = metaParts.length > 0 ? metaParts.join(" • ") : null;
      if (name && meta) {
        return `${name} (${meta})`;
      }
      if (name) {
        return name;
      }
      if (meta) {
        return meta;
      }
      return "-";
    },
    [translateScopeLevel]
  );

  const formatDateTime = useCallback((value?: string | null) => {
    if (!value) {
      return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString("th-TH", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }, []);

  const detailContent = useMemo(() => {
    if (!detailPayload) {
      if (detailTarget) {
        return <p className="text-sm text-slate-500">กำลังดึงรายละเอียด</p>;
      }
      return null;
    }

    if (detailPayload.kind === "osm") {
      const detail = detailPayload.data;
      const fullNameParts = [detail.prefix_name_th, detail.first_name, detail.last_name].filter(
        (part): part is string => typeof part === "string" && part.trim().length > 0
      );
      const fullName = fullNameParts.join(" ");
      const villageDisplay = detail.village_name
        ? detail.village_no
          ? `${detail.village_name} (หมู่ ${detail.village_no})`
          : detail.village_name
        : displayValue(detail.village_no);
      const addressParts = [detail.address_number, detail.street, detail.alley].filter((part) => typeof part === "string" && part.trim().length > 0) as string[];
      const address = addressParts.length > 0 ? addressParts.join(" ") : "-";
      const bankDisplay = detail.bank_name_th
        ? `${detail.bank_name_th}${detail.bank_account_number ? ` (${detail.bank_account_number})` : ""}`
        : displayValue(detail.bank_account_number ?? detail.bank_name_th);

      const locationParts = [detail.province_name_th, detail.district_name_th, detail.subdistrict_name_th].filter(Boolean);
      const locationDisplay = locationParts.length > 0 ? locationParts.join(" / ") : "-";

      return (
        <div className="space-y-4">
          <DetailSection
            title="ข้อมูลส่วนบุคคล"
            fields={[
              { label: "ชื่อ-สกุล", value: fullName || detailTarget?.full_name || "-" },
              {
                label: "เลขบัตรประชาชน",
                value: detail.citizen_id ? (
                  <SensitiveValue
                    value={detail.citizen_id}
                    maskSuffix={4}
                    valueClassName="font-mono text-xs text-slate-700"
                    buttonClassName="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:border-slate-300 hover:bg-slate-100"
                  />
                ) : (
                  <span className="text-slate-400">-</span>
                ),
              },
              { label: "เลขบัตร อสม.", value: displayValue(detail.osmCode ?? detail.osm_code) },
              { label: "เพศ", value: translateGender(detail.gender) },
              { label: "วันเกิด", value: formatBirthDateWithAge(detail.birth_date) },
              { label: "สถานภาพสมรส", value: translateMaritalStatus(detail.marital_status) },
              { label: "จำนวนบุตร", value: detail.number_of_children !== null && detail.number_of_children !== undefined ? detail.number_of_children : "-" },
              { label: "หมู่เลือด", value: translateBloodType(detail.blood_type) },
              { label: "ปีที่ขึ้นทะเบียน", value: detail.osm_year !== null && detail.osm_year !== undefined ? detail.osm_year : "-" },
              { label: "มีสมาร์ทโฟน", value: detail.is_smartphone_owner === true ? "มี" : detail.is_smartphone_owner === false ? "ไม่มี" : "-" },
            ]}
          />
          <DetailSection
            title="สถานะและสิทธิ์"
            fields={[
              { label: "สถานะ อสม.", value: translateOsmStatus(detail.osm_status) },
              { label: "สถานะการอนุมัติ", value: translateApprovalStatus(detail.approval_status) },
              { label: "สถานะค่าป่วยการ", value: translateShowbody(detail.showbody ?? detail.osm_showbbody) },
              { label: "สถานะระบบ", value: detail.is_active ? "เปิดใช้งาน" : "ปิดใช้งาน" },
            ]}
          />
          <DetailSection
            title="ที่อยู่และพื้นที่"
            fields={[
              { label: "จังหวัด", value: displayValue(detail.province_name_th) },
              { label: "อำเภอ", value: displayValue(detail.district_name_th) },
              { label: "ตำบล", value: displayValue(detail.subdistrict_name_th) },
              { label: "หมู่บ้าน", value: villageDisplay },
              { label: "รหัสหมู่บ้าน", value: displayValue(detail.village_code) },
              { label: "ที่อยู่", value: address },
              { label: "รหัสไปรษณีย์", value: displayValue(detail.postal_code) },
            ]}
          />
          <DetailSection
            title="ช่องทางติดต่อและอื่นๆ"
            fields={[
              { label: "โทรศัพท์", value: displayValue(detail.phone) },
              { label: "อีเมล", value: displayValue(detail.email) },
              { label: "หน่วยบริการสุขภาพ", value: displayValue(detail.health_service_name_th) },
              { label: "อาชีพ", value: displayValue(detail.occupation_name_th) },
              { label: "การศึกษา", value: displayValue(detail.education_name_th) },
              { label: "บัญชีธนาคาร", value: bankDisplay },
            ]}
          />
          <DetailSection
            title="การจัดการระบบ"
            fields={[
              {
                label: "สร้างโดย",
                value: describeActor(detail.created_by_name, detail.created_by_position_name, detail.created_by_scope_label, detail.created_by_scope_level),
              },
              { label: "สร้างเมื่อ", value: formatDateTime(detail.created_at) },
              {
                label: "ปรับปรุงโดย",
                value: describeActor(detail.updated_by_name, detail.updated_by_position_name, detail.updated_by_scope_label, detail.updated_by_scope_level),
              },
              { label: "ปรับปรุงเมื่อ", value: formatDateTime(detail.updated_at) },
              {
                label: "อนุมัติโดย",
                value: describeActor(detail.approval_by_name, detail.approval_by_position_name, detail.approval_by_scope_label, detail.approval_by_scope_level),
              },
              { label: "อนุมัติเมื่อ", value: formatDateTime(detail.approval_date) },
            ]}
          />
        </div>
      );
    }

    if (detailPayload.kind === "yuwa_osm") {
      const detail = detailPayload.data;
      const fullName = `${detail.first_name} ${detail.last_name}`.trim();

      return (
        <div className="space-y-6">
          <DetailSection
            title="ข้อมูลพื้นฐาน"
            fields={[
              { label: "ชื่อ-สกุล", value: fullName || detailTarget?.full_name || "-" },
              {
                label: "เลขบัตรประชาชน",
                value: detail.citizen_id ? (
                  <SensitiveValue
                    value={detail.citizen_id}
                    maskSuffix={4}
                    valueClassName="font-mono text-xs text-slate-700"
                    buttonClassName="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:border-slate-300 hover:bg-slate-100"
                  />
                ) : (
                  <span className="text-slate-400">-</span>
                ),
              },
              { label: "รหัสยุวอสม.", value: displayValue(detail.yuwa_osm_code) },
              { label: "เพศ", value: translateGender(detail.gender) },
              { label: "วันเกิด", value: formatBirthDateWithAge(detail.birthday) },
              { label: "สถานะการใช้งาน", value: detail.is_active ? "พร้อมใช้งาน" : "ปิดใช้งาน" },
            ]}
          />
          <DetailSection
            title="ช่องทางติดต่อ"
            fields={[
              { label: "โทรศัพท์", value: displayValue(detail.phone_number) },
              { label: "อีเมล", value: displayValue(detail.email) },
              { label: "Line ID", value: displayValue(detail.line_id) },
              { label: "โรงเรียน", value: displayValue(detail.school) },
              { label: "หน่วยงาน", value: displayValue(detail.organization) },
            ]}
          />
          <DetailSection
            title="พื้นที่ที่เกี่ยวข้อง"
            fields={[
              { label: "จังหวัด", value: displayValue(detail.province_name) },
              { label: "อำเภอ", value: displayValue(detail.district_name) },
              { label: "ตำบล", value: displayValue(detail.subdistrict_name) },
            ]}
          />
          <DetailSection
            title="การจัดการระบบ"
            fields={[
              { label: "สร้างเมื่อ", value: formatDateTime(detail.created_at) },
              { label: "ปรับปรุงเมื่อ", value: formatDateTime(detail.updated_at) },
              {
                label: "อนุมัติโดย",
                value: describeActor(detail.approved_by_name, detail.approved_by_position_name, detail.approved_by_scope_label, detail.approved_by_scope_level),
              },
              { label: "อนุมัติเมื่อ", value: formatDateTime(detail.approved_at) },
              {
                label: "ผู้ปฏิเสธ",
                value: describeActor(
                  detail.rejected_by_name,
                  detail.rejected_by_position_name,
                  detail.rejected_by_scope_label,
                  detail.rejected_by_scope_level
                ),
              },
              { label: "เหตุผลการปฏิเสธ", value: displayValue(detail.rejection_reason) },
            ]}
          />
        </div>
      );
    }

    if (detailPayload.kind === "people") {
      const detail = detailPayload.data;
      const fullName = `${detail.first_name} ${detail.last_name}`.trim();

      return (
        <div className="space-y-6">
          <DetailSection
            title="ข้อมูลพื้นฐาน"
            fields={[
              { label: "ชื่อ-สกุล", value: fullName || detailTarget?.full_name || "-" },
              {
                label: "เลขบัตรประชาชน",
                value: detail.citizen_id ? (
                  <SensitiveValue
                    value={detail.citizen_id}
                    maskSuffix={4}
                    valueClassName="font-mono text-xs text-slate-700"
                    buttonClassName="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:border-slate-300 hover:bg-slate-100"
                  />
                ) : (
                  <span className="text-slate-400">-</span>
                ),
              },
              { label: "รหัสยุวอสม.", value: displayValue(detail.yuwa_osm_code) },
              { label: "เพศ", value: translateGender(detail.gender) },
              { label: "วันเกิด", value: formatBirthDateWithAge(detail.birthday) },
              { label: "สถานะการใช้งาน", value: detail.is_active ? "พร้อมใช้งาน" : "ปิดใช้งาน" },
            ]}
          />
          <DetailSection
            title="สถานะการย้าย"
            fields={[
              { label: "สถานะ", value: detail.is_transferred ? "ย้ายแล้ว" : "ยังไม่ย้าย" },
              { label: "รหัสยุวอสม.", value: displayValue(detail.yuwa_osm_code) },
              { label: "ย้ายเมื่อ", value: formatDateTime(detail.transferred_at ?? undefined) },
              {
                label: "ผู้ทำรายการ",
                value: displayValue(detail.transferred_by_name) || getActorDisplay(detail.transferred_by),
              },
            ]}
          />
          <DetailSection
            title="ช่องทางติดต่อ"
            fields={[
              { label: "โทรศัพท์", value: displayValue(detail.phone_number) },
              { label: "อีเมล", value: displayValue(detail.email) },
              { label: "โรงเรียน", value: displayValue(detail.school) },
              { label: "หน่วยงาน", value: displayValue(detail.organization) },
            ]}
          />
          <DetailSection
            title="พื้นที่ที่เกี่ยวข้อง"
            fields={[
              { label: "จังหวัด", value: displayValue(detail.province_name) },
              { label: "อำเภอ", value: displayValue(detail.district_name) },
              { label: "ตำบล", value: displayValue(detail.subdistrict_name) },
            ]}
          />
          <DetailSection
            title="การจัดการระบบ"
            fields={[
              { label: "สร้างเมื่อ", value: formatDateTime(detail.created_at ?? undefined) },
              { label: "ปรับปรุงเมื่อ", value: formatDateTime(detail.updated_at ?? undefined) },
            ]}
          />
        </div>
      );
    }

    if (detailPayload.kind === "gen_h") {
      const detail = detailPayload.data;
      const fullName = [detail.prefix, detail.first_name, detail.last_name].filter(Boolean).join(" ");

      return (
        <div className="space-y-6">
          <DetailSection
            title="ข้อมูลพื้นฐาน"
            fields={[
              { label: "ชื่อ-สกุล", value: fullName || detailTarget?.full_name || "-" },
              { label: "รหัสบัตรสมาชิก", value: displayValue(detail.gen_h_code) },
              {
                label: "บัตรประจำตัว GenH",
                value: detail.member_card_url ? (
                  <a
                    href={detail.member_card_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700 ring-1 ring-amber-200 transition hover:bg-amber-100 hover:ring-amber-300"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                      <path d="M4.5 3.75a.75.75 0 0 0-.75.75v11a.75.75 0 0 0 .75.75h11a.75.75 0 0 0 .75-.75v-3.5a.75.75 0 0 1 1.5 0v3.5A2.25 2.25 0 0 1 15.5 18h-11A2.25 2.25 0 0 1 2.25 15.5v-11A2.25 2.25 0 0 1 4.5 2.25h3.5a.75.75 0 0 1 0 1.5h-3.5Z" />
                      <path d="M6.22 8.72a.75.75 0 0 1 1.06 0l2.22 2.22V4.5a.75.75 0 0 1 1.5 0v6.44l2.22-2.22a.75.75 0 1 1 1.06 1.06l-3.5 3.5a.75.75 0 0 1-1.06 0l-3.5-3.5a.75.75 0 0 1 0-1.06Z" />
                    </svg>
                    ดูบัตร PDF
                  </a>
                ) : (
                  <span className="text-slate-400">-</span>
                ),
              },
              { label: "เพศ", value: translateGender(detail.gender) },
              { label: "คะแนนสะสม", value: detail.points ?? 0 },
              { label: "สถานะการใช้งาน", value: detail.is_active ? "พร้อมใช้งาน" : "ปิดใช้งาน" },
            ]}
          />
          <DetailSection
            title="สถานะการย้าย"
            fields={[
              { label: "สถานะ", value: detail.people_user_id ? "ย้ายเป็นประชาชนแล้ว" : detail.yuwa_osm_user_id ? "ย้ายเป็นยุวอสม.แล้ว" : "ยังไม่ย้าย" },
              { label: "ย้ายเมื่อ", value: formatDateTime(detail.transferred_at ?? undefined) },
            ]}
          />
          <DetailSection
            title="ช่องทางติดต่อ"
            fields={[
              { label: "โทรศัพท์", value: displayValue(detail.phone_number) },
              { label: "อีเมล", value: displayValue(detail.email) },
              { label: "Line ID", value: displayValue(detail.line_id) },
              { label: "โรงเรียน", value: displayValue(detail.school) },
            ]}
          />
          <DetailSection
            title="พื้นที่ที่เกี่ยวข้อง"
            fields={[
              { label: "จังหวัด", value: displayValue(detail.province_name) },
              { label: "อำเภอ", value: displayValue(detail.district_name) },
              { label: "ตำบล", value: displayValue(detail.subdistrict_name) },
            ]}
          />
          <DetailSection
            title="การจัดการระบบ"
            fields={[
              { label: "สร้างเมื่อ", value: formatDateTime(detail.created_at ?? undefined) },
              { label: "ปรับปรุงเมื่อ", value: formatDateTime(detail.updated_at ?? undefined) },
            ]}
          />
        </div>
      );
    }

    const candidate = detailPayload.data;
    const typeLabel = typeLabels[resolveCommunityType(candidate.user_type)];

    return (
      <div className="space-y-6">
        <DetailSection
          title="ข้อมูลพื้นฐาน"
          fields={[
            { label: "ชื่อ-สกุล", value: displayValue(candidate.full_name) },
            {
              label: "เลขบัตรประชาชน",
              value: candidate.citizen_id ? (
                <SensitiveValue
                  value={candidate.citizen_id}
                  maskSuffix={4}
                  valueClassName="font-mono text-xs text-slate-700"
                  buttonClassName="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-semibold text-slate-600 hover:border-slate-300 hover:bg-slate-100"
                />
              ) : (
                <span className="text-slate-400">-</span>
              ),
            },
            { label: "ประเภทผู้ใช้", value: typeLabel },
            { label: "สถานะการใช้งาน", value: candidate.is_active ? "พร้อมใช้งาน" : "ปิดใช้งาน" },
            ...(candidate.user_type === "people"
              ? [
                  { label: "สถานะการย้าย", value: candidate.is_transferred ? "ย้ายแล้ว" : "ยังไม่ย้าย" },
                  { label: "รหัสยุวอสม.", value: displayValue(candidate.yuwa_osm_code) },
                  { label: "ย้ายเมื่อ", value: formatDateTime(candidate.transferred_at ?? undefined) },
                  { label: "ผู้ทำรายการ", value: getActorDisplay(candidate.transferred_by) },
                ]
              : []),
          ]}
        />
        <DetailSection
          title="ช่องทางติดต่อ"
          fields={[
            { label: "โทรศัพท์", value: displayValue(candidate.phone) },
            { label: "อีเมล", value: displayValue(candidate.email) },
            { label: "หน่วยงาน/โรงเรียน", value: displayValue(candidate.organization) },
          ]}
        />
        <DetailSection
          title="พื้นที่"
          fields={[
            { label: "จังหวัด", value: displayValue(candidate.province_name) },
            { label: "อำเภอ", value: displayValue(candidate.district_name) },
            { label: "ตำบล", value: displayValue(candidate.subdistrict_name) },
          ]}
        />
      </div>
    );
  }, [detailPayload, detailTarget, displayValue, formatDateTime, typeLabels, translateGender, describeActor, getActorDisplay]);

  const detailTitle = useMemo(() => {
    if (!detailTarget) {
      return "รายละเอียด";
    }
    const typeLabel = typeLabels[resolveCommunityType(detailTarget.user_type)];
    let resolvedName: string | undefined;
    if (detailPayload?.kind === "osm") {
      const detail = detailPayload.data;
      const nameParts = [detail.prefix_name_th, detail.first_name, detail.last_name].filter(
        (part): part is string => typeof part === "string" && part.trim().length > 0
      );
      resolvedName = nameParts.join(" ");
    } else if (detailPayload?.kind === "yuwa_osm") {
      const detail = detailPayload.data;
      resolvedName = `${detail.first_name} ${detail.last_name}`.trim();
    } else if (detailPayload?.kind === "people") {
      const detail = detailPayload.data;
      resolvedName = `${detail.first_name} ${detail.last_name}`.trim();
    } else if (detailPayload?.kind === "gen_h") {
      const detail = detailPayload.data;
      resolvedName = [detail.prefix, detail.first_name, detail.last_name].filter(Boolean).join(" ");
    } else {
      resolvedName = detailTarget.full_name;
    }
    const suffix = resolvedName && resolvedName.length > 0 ? ` - ${resolvedName}` : detailTarget.full_name ? ` - ${detailTarget.full_name}` : "";
    return `รายละเอียด${typeLabel ? ` ${typeLabel}` : ""}${suffix}`;
  }, [detailTarget, detailPayload, typeLabels]);

  const detailDimmed = useMemo(() => {
    if (!detailTarget) {
      return false;
    }
    if (detailPayload?.kind === "people") {
      const detail = detailPayload.data;
      const transferred = Boolean(detail.is_transferred) || Boolean(detail.yuwa_osm_id);
      return transferred || !detail.is_active;
    }
    if (detailPayload?.kind === "osm" || detailPayload?.kind === "yuwa_osm") {
      return !detailPayload.data.is_active;
    }
    if (detailPayload?.kind === "gen_h") {
      const detail = detailPayload.data;
      const transferred = Boolean(detail.people_user_id) || Boolean(detail.yuwa_osm_user_id);
      return transferred || !detail.is_active;
    }
    if (detailPayload?.kind === "candidate") {
      const candidate = detailPayload.data;
      const transferred = Boolean(candidate.is_transferred) || Boolean(candidate.yuwa_osm_id);
      return transferred || !candidate.is_active;
    }
    return false;
  }, [detailPayload, detailTarget]);

  return (
    <div className="space-y-8">
      <header className="rounded-2xl bg-gradient-to-r from-emerald-600 via-teal-500 to-sky-500 p-6 text-white shadow-lg">
        <div className="flex flex-col gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-white/80">Department Tools</p>
            <h1 className="text-2xl font-bold">{title}</h1>
            {subtitle ? <p className="text-sm text-white/80">{subtitle}</p> : null}
          </div>
          <p className="text-sm text-white/80">{description}</p>
          {helperText ? <p className="text-xs text-white/70">{helperText}</p> : null}
          {headerActions ? <div className="pt-2 text-white/90">{headerActions}</div> : null}
        </div>
        {introHighlights && introHighlights.length > 0 ? (
          <dl className="mt-4 grid gap-3 sm:grid-cols-3">
            {introHighlights.map((item) => (
              <div key={item.label} className="rounded-xl border border-white/20 bg-white/10 p-4 shadow-inner">
                <dt className="text-xs font-semibold uppercase tracking-wide text-white/70">{item.label}</dt>
                <dd className="mt-1 text-sm font-medium text-white">{item.detail}</dd>
              </div>
            ))}
          </dl>
        ) : null}
      </header>

      <section className="space-y-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <input
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder={placeholder}
              className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 pr-12 text-sm font-medium text-slate-700 shadow-sm transition focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
            />
            <span className="pointer-events-none absolute inset-y-0 right-4 flex items-center text-slate-400">
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-4.35-4.35m0 0A7.5 7.5 0 1 0 8.5 15.5a7.5 7.5 0 0 0 8.15 1.15Z" />
              </svg>
            </span>
          </div>
          <button
            type="submit"
            className="inline-flex h-12 items-center justify-center rounded-xl bg-emerald-600 px-6 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
          >
            ค้นหา
          </button>
        </form>

        {temporaryReset ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 shadow-inner">
            <p className="font-semibold">
              สร้างรหัสผ่านชั่วคราวใหม่ให้ {temporaryReset.name} ({typeLabels[temporaryReset.userType as Extract<UserType, "osm" | "yuwa_osm" | "people" | "gen_h">]}) แล้ว
            </p>
            <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <code className="rounded-lg bg-white px-3 py-2 text-base font-semibold tracking-wide text-amber-700 shadow">
                {temporaryReset.password}
              </code>
              <button
                type="button"
                onClick={handleCopyTemporaryPassword}
                className="inline-flex items-center justify-center rounded-lg border border-amber-300 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-700 transition hover:border-amber-400 hover:bg-amber-100"
              >
                {copiedTempPassword ? "คัดลอกแล้ว" : "คัดลอกรหัสผ่าน"}
              </button>
            </div>
            <p className="mt-2 text-xs text-amber-600">โปรดแจ้งผู้ใช้งานให้เปลี่ยนรหัสผ่านทันทีหลังเข้าสู่ระบบ</p>
          </div>
        ) : null}

        {resetError ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-inner">
            {resetError}
          </div>
        ) : null}

        {statusNotice ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 shadow-inner">
            {statusNotice}
          </div>
        ) : null}

        {statusError ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-inner">
            {statusError}
          </div>
        ) : null}

        <div ref={resultsPanelRef} className="rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 text-sm text-slate-500">
            <span>ผลการค้นหา</span>
            <span className="font-semibold text-slate-700">{resultSummary}</span>
          </div>

          {error ? (
            <div className="px-6 py-4 text-sm text-rose-600">{error}</div>
          ) : null}

          {loading ? (
            <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-slate-500">
              <svg className="h-8 w-8 animate-spin text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" />
                <path className="opacity-75" d="M12 2a10 10 0 0 1 10 10h-3a7 7 0 0 0-7-7V2Z" fill="currentColor" />
              </svg>
              <span className="text-sm font-medium">กำลังรวบรวมข้อมูล</span>
            </div>
          ) : displayedResults.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">ผู้ใช้</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">เลขบัตรประชาชน</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">ช่องทางติดต่อ</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">พื้นที่</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">หน่วยงาน / บทบาท</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">การจัดการ</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {displayedResults.map((item) => {
                    const communityType = resolveCommunityType(item.user_type);
                    const canManage = canManageCandidate(item);
                    const pendingForItem = resetBusy && resetTarget?.user_id === item.user_id;
                    const statusPending = statusBusyId === item.user_id;
                    const nextStatusLabel = item.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน";
                    const isTransferred =
                      communityType === "people" &&
                      (Boolean(item.is_transferred) || Boolean(item.yuwa_osm_id));
                    const transferTargetLabel =
                      communityType === "people" && isTransferred
                        ? "ย้ายไป Yuwa OSM"
                        : null;
                    const isDimmed = isTransferred || !item.is_active;
                    return (
                      <tr
                        key={item.user_id}
                        className={`transition hover:bg-slate-50 ${isDimmed ? "bg-slate-50" : ""}`}
                      >
                      <td className="px-6 py-4 text-sm text-slate-800">
                        <div className="flex flex-col gap-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-slate-900">{item.full_name || "ไม่ระบุ"}</span>
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                                typeBadgeClasses[communityType]
                              }`}
                            >
                              {typeLabels[communityType]}
                            </span>
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                item.is_active ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"
                              }`}
                            >
                              {item.is_active ? "พร้อมใช้งาน" : "ปิดใช้งาน"}
                            </span>
                            {transferTargetLabel ? (
                              <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                                {transferTargetLabel}
                              </span>
                            ) : null}
                          </div>
                          <code className="inline-flex w-fit items-center gap-1 rounded bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700">
                            <span className="text-[10px] uppercase tracking-wide text-slate-500">ID</span>
                            {item.user_id}
                          </code>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-700">
                        {item.citizen_id ? (
                          <SensitiveValue
                            value={item.citizen_id}
                            className="inline-flex items-center gap-1"
                            valueClassName="font-mono text-xs text-slate-700"
                            buttonClassName="rounded-full border border-slate-200 p-1 text-slate-500 hover:border-slate-300 hover:bg-slate-100"
                          />
                        ) : (
                          <span className="text-xs text-slate-400">ไม่ระบุ</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-700">
                        <div className="flex flex-col gap-1 text-xs">
                          {item.phone ? <span className="font-medium text-slate-700">โทร: {item.phone}</span> : null}
                          {item.email ? <span className="text-slate-600">อีเมล: {item.email}</span> : null}
                          {!item.phone && !item.email ? <span className="text-slate-400">ไม่ระบุ</span> : null}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-700">
                        <div className="flex flex-col gap-1 text-xs">
                          {item.province_name ? <span>จังหวัด {item.province_name}</span> : null}
                          {item.district_name ? <span>อำเภอ {item.district_name}</span> : null}
                          {item.subdistrict_name ? <span>ตำบล {item.subdistrict_name}</span> : null}
                          {!item.province_name && !item.district_name && !item.subdistrict_name ? (
                            <span className="text-slate-400">ไม่ระบุ</span>
                          ) : null}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-700">
                        <div className="flex flex-col gap-1 text-xs">
                          {item.organization ? <span>หน่วยงาน: {item.organization}</span> : null}
                          {item.role ? <span>บทบาท: {item.role}</span> : null}
                          {!item.organization && !item.role ? <span className="text-slate-400">ไม่ระบุ</span> : null}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right text-sm text-slate-700">
                        <div className="flex items-center justify-end gap-2">
                          <IconButton
                            label="ดูรายละเอียด"
                            onClick={() => handleOpenDetails(item)}
                            tone="info"
                            disabled={detailBusy && detailTarget?.user_id === item.user_id}
                            busy={detailBusy && detailTarget?.user_id === item.user_id}
                          >
                            <IconInfo className="h-5 w-5" />
                          </IconButton>
                          <IconButton
                            label={statusPending ? "กำลังปรับสถานะ" : nextStatusLabel}
                            onClick={() => handleToggleStatus(item)}
                            disabled={!canManage || statusPending || !hasCommunityScope}
                            tone={item.is_active ? "danger" : "success"}
                            busy={statusPending}
                          >
                            <IconPower className="h-5 w-5" />
                          </IconButton>
                          <IconButton
                            label={pendingForItem ? "กำลังรีเซ็ตรหัสผ่าน" : "รีเซ็ตรหัสผ่าน"}
                            onClick={() => handleOpenReset(item)}
                            disabled={!canManage || pendingForItem || !hasCommunityScope}
                            tone="warning"
                            busy={pendingForItem}
                          >
                            <IconKey className="h-5 w-5" />
                          </IconButton>
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="px-6 py-12 text-center text-sm text-slate-500">
              {hasSearched ? "ไม่พบข้อมูลที่ตรงกับคำค้น" : "กรุณากรอกคำค้นเพื่อค้นหา"}
            </div>
          )}

          {hasSearched && total > limit && !loading ? (
            <div className="flex flex-col items-center gap-3 border-t border-slate-200 px-6 py-4 sm:flex-row sm:justify-between">
              <span className="text-xs text-slate-500">
                หน้า {currentPage} จาก {totalPages} ({total} รายการ)
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={handlePrevPage}
                  disabled={!hasPrev}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-sm text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="หน้าก่อนหน้า"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" /></svg>
                </button>
                {(() => {
                  const pages: (number | "dots")[] = [];
                  if (totalPages <= 7) {
                    for (let i = 1; i <= totalPages; i++) pages.push(i);
                  } else {
                    pages.push(1);
                    if (currentPage > 3) pages.push("dots");
                    const start = Math.max(2, currentPage - 1);
                    const end = Math.min(totalPages - 1, currentPage + 1);
                    for (let i = start; i <= end; i++) pages.push(i);
                    if (currentPage < totalPages - 2) pages.push("dots");
                    pages.push(totalPages);
                  }
                  return pages.map((p, idx) =>
                    p === "dots" ? (
                      <span key={`dots-${idx}`} className="px-1 text-xs text-slate-400">…</span>
                    ) : (
                      <button
                        key={p}
                        type="button"
                        onClick={() => handleGoToPage(p)}
                        className={`inline-flex h-8 min-w-[2rem] items-center justify-center rounded-lg border text-xs font-semibold transition ${
                          p === currentPage
                            ? "border-emerald-500 bg-emerald-500 text-white shadow-sm"
                            : "border-slate-200 text-slate-600 hover:bg-slate-100"
                        }`}
                      >
                        {p}
                      </button>
                    )
                  );
                })()}
                <button
                  type="button"
                  onClick={handleNextPage}
                  disabled={!hasNext}
                  className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-sm text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
                  aria-label="หน้าถัดไป"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" /></svg>
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </section>

      <DetailDialog
        open={Boolean(detailTarget)}
        title={detailTitle}
        onClose={handleCloseDetails}
        busy={detailBusy}
        error={detailError}
        dimmed={detailDimmed}
      >
        {detailContent}
      </DetailDialog>

      <ConfirmDialog
        open={Boolean(resetTarget)}
        title="ยืนยันการรีเซ็ตรหัสผ่าน"
        message={`ระบบจะสร้างรหัสผ่านชั่วคราวใหม่ให้ ${resetTarget?.full_name ?? "ผู้ใช้งาน"}\nรหัสผ่านเดิมทั้งหมดจะไม่สามารถใช้งานได้ทันที`}
        confirmLabel="รีเซ็ตรหัสผ่าน"
        cancelLabel="ยกเลิก"
        variant="default"
        onCancel={handleCloseReset}
        onConfirm={handleConfirmReset}
        busy={resetBusy}
      />
    </div>
  );
};

export default QuickSearchPage;
