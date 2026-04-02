import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  fetchOfficer,
  setOfficerActiveStatus,
  updateOfficer,
  deleteOfficer,
  resetOfficerPassword,
  approveOfficer,
  rejectOfficer,
  transferOfficer,
  fetchOfficerTransferHistory,
  fetchOfficerDisplayMetaById,
} from "../api/officers";
import type {
  OfficerDetail,
  OfficerUpdatePayload,
  AdministrativeLevel,
  OfficerPasswordResetResult,
  OfficerTransferPayload,
  OfficerTransferHistoryItem,
} from "../types/officer";
import { OfficerForm } from "../components/OfficerForm";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { PageLoader } from "../components/ui/PageLoader";
import { OfficerTransferDialog } from "../components/OfficerTransferDialog";
import { useAuthContext } from "../context/AuthContext";
import {
  SensitiveValue,
  EyeIcon,
  EyeOffIcon,
} from "../components/ui/SensitiveValue";

const AREA_TYPE_LABELS: Record<AdministrativeLevel, string> = {
  village: "หมู่บ้าน",
  subdistrict: "ตำบล",
  district: "อำเภอ",
  province: "จังหวัด",
  area: "เขตสุขภาพ",
  region: "ภาค",
  country: "ประเทศ",
};

const APPROVAL_STATUS_LABELS: Record<string, string> = {
  approved: "อนุมัติแล้ว",
  pending: "รออนุมัติ",
  rejected: "ปฏิเสธแล้ว",
};

const BANGKOK_FORMATTER = new Intl.DateTimeFormat("th-TH", {
  dateStyle: "medium",
  timeStyle: "medium",
  timeZone: "Asia/Bangkok",
});

const formatBangkokDateTime = (value?: string | null) => {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  const formatted = BANGKOK_FORMATTER.format(parsed);
  return `${formatted} (Bangkok +07:00)`;
};

const renderAreaType = (value?: AdministrativeLevel | null) => {
  if (!value) {
    return "-";
  }
  return AREA_TYPE_LABELS[value] ?? value;
};

const getTextValue = (
  data: Record<string, unknown> | null | undefined,
  key: string,
) => {
  const value = data?.[key];
  return typeof value === "string" && value.trim() ? value : "";
};

const renderTransferLocation = (
  data: Record<string, unknown> | null | undefined,
) => {
  const parts = [
    {
      label: "เขตสุขภาพ",
      value: getTextValue(data, "health_area_name_th"),
    },
    { label: "จังหวัด", value: getTextValue(data, "province_name_th") },
    { label: "อำเภอ", value: getTextValue(data, "district_name_th") },
    { label: "ตำบล", value: getTextValue(data, "subdistrict_name_th") },
    {
      label: "หน่วยบริการ",
      value: getTextValue(data, "health_service_name_th"),
    },
  ].filter((item) => item.value);

  if (!parts.length) {
    return "-";
  }

  const areaType = typeof data?.area_type === "string" ? data.area_type : "";
  const levelLabel = areaType
    ? (AREA_TYPE_LABELS as Record<string, string>)[areaType] ?? areaType
    : "";
  const locationStr = parts
    .map((item) => `${item.label}${item.value}`)
    .join(" / ");
  return levelLabel ? `[${levelLabel}] ${locationStr}` : locationStr;
};

const OfficerDetailPage: React.FC = () => {
  const { officerId } = useParams<{ officerId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuthContext();
  const backToListPath = location.search ? `/officers${location.search}` : "/officers";
  const [officer, setOfficer] = useState<OfficerDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [updating, setUpdating] = useState<boolean>(false);
  const [toggling, setToggling] = useState<boolean>(false);
  const [approving, setApproving] = useState<boolean>(false);
  const [rejecting, setRejecting] = useState<boolean>(false);
  const [deleting, setDeleting] = useState<boolean>(false);
  const [transferOpen, setTransferOpen] = useState<boolean>(false);
  const [transferBusy, setTransferBusy] = useState<boolean>(false);
  const [transferHistory, setTransferHistory] = useState<
    OfficerTransferHistoryItem[]
  >([]);
  const [canLoadTransferHistory, setCanLoadTransferHistory] =
    useState<boolean>(false);
  const [transferHistoryLoading, setTransferHistoryLoading] =
    useState<boolean>(false);
  const [transferByMap, setTransferByMap] = useState<
    Record<string, { name: string | null; level: string | null }>
  >({});
  const [confirmState, setConfirmState] = useState<
    "toggle" | "delete" | "reset" | "approve" | "reject" | null
  >(null);
  const [resettingPassword, setResettingPassword] = useState<boolean>(false);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(
    null,
  );
  const [copiedTempPassword, setCopiedTempPassword] = useState<boolean>(false);
  const pendingRequestRef = useRef<{
    key: string;
    promise: Promise<OfficerDetail>;
  } | null>(null); // re-use detail fetches to avoid duplicate calls

  useEffect(() => {
    if (!officerId) {
      return;
    }
    setTemporaryPassword(null);
    setCopiedTempPassword(false);
    setConfirmState(null);
    setIsEditing(false);
    setCanLoadTransferHistory(false);
    const requestKey = officerId;
    let isCurrent = true;

    setLoading(true);
    setError(null);

    const runRequest = () => {
      if (pendingRequestRef.current?.key === requestKey) {
        return pendingRequestRef.current.promise;
      }

      const promise = fetchOfficer(officerId);
      pendingRequestRef.current = { key: requestKey, promise };
      promise.finally(() => {
        if (pendingRequestRef.current?.key === requestKey) {
          pendingRequestRef.current = null;
        }
      });
      return promise;
    };

    runRequest()
      .then((data) => {
        if (!isCurrent) {
          return;
        }
        setOfficer(data);
        setCanLoadTransferHistory(true);
      })
      .catch((err: any) => {
        if (!isCurrent) {
          return;
        }
        const detail = err?.response?.data?.detail;
        if (detail === "insufficient_scope_view_record") {
          setError("คุณไม่มีสิทธิ์ดูข้อมูลเจ้าหน้าที่รายนี้");
          return;
        }
        setError("ไม่พบข้อมูลเจ้าหน้าที่หรือเกิดข้อผิดพลาด");
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
  }, [officerId]);

  const permissions = officer?.permissions;
  const canEdit = permissions ? permissions.can_edit : true;
  const canToggleActive = permissions ? permissions.can_toggle_active : true;
  const canResetPassword = permissions ? permissions.can_reset_password : true;
  const canDelete = permissions ? permissions.can_delete : true;
  const canApprove = permissions ? permissions.can_approve : true;
  const canTransfer = permissions ? permissions.can_transfer : true;
  const userPositionName = String(user?.position_name_th ?? "").trim();
  const actorLevel = user?.permission_scope?.level ?? user?.position_scope_level ?? null;
  const hideTransferForLocalOperator =
    actorLevel === "subdistrict" ||
    actorLevel === "village" ||
    user?.position_scope_level === "subdistrict" ||
    user?.position_scope_level === "village" ||
    userPositionName.includes("รพ.สต") ||
    userPositionName.includes("รพสต");
  const showTransferButton = canTransfer && !hideTransferForLocalOperator;
  const showPeerRestrictionNotice = Boolean(
    permissions && permissions.is_same_level && !permissions.can_toggle_active,
  );

  const mapErrorDetailToMessage = (detail?: string | null) => {
    if (!detail) {
      return null;
    }
    if (detail === "insufficient_scope_same_level") {
      return "คุณไม่มีสิทธิ์จัดการเจ้าหน้าที่ที่อยู่ในระดับเดียวกัน";
    }
    if (detail === "insufficient_scope_self_action") {
      return "ไม่สามารถดำเนินการกับบัญชีของตนเองได้";
    }
    if (detail === "insufficient_scope_transfer") {
      return "คุณไม่มีสิทธิ์โยกย้ายเจ้าหน้าที่ในระดับนี้";
    }
    if (detail === "insufficient_scope") {
      return "คุณไม่มีสิทธิ์จัดการบัญชีนี้";
    }
    if (detail === "insufficient_scope_view_record") {
      return "คุณไม่มีสิทธิ์ดูข้อมูลเจ้าหน้าที่รายนี้";
    }
    if (detail === "invalid_location_hierarchy") {
      return "ข้อมูลพื้นที่ปลายทางไม่สัมพันธ์กัน กรุณาเลือกจังหวัด/อำเภอ/ตำบลใหม่ให้ถูกต้อง";
    }
    if (detail === "province_not_found" || detail === "district_not_found" || detail === "subdistrict_not_found") {
      return "ไม่พบข้อมูลพื้นที่ปลายทางที่เลือก กรุณาเลือกใหม่";
    }
    if (detail === "health_service_required") {
      return "ระดับนี้ต้องระบุหน่วยบริการสุขภาพปลายทาง";
    }
    if (detail === "creator_not_active") {
      return "บัญชีของคุณยังไม่เปิดใช้งาน จึงไม่สามารถดำเนินการได้";
    }
    return null;
  };

  useEffect(() => {
    if (!canEdit && isEditing) {
      setIsEditing(false);
    }
  }, [canEdit, isEditing]);

  useEffect(() => {
    if (!officerId || !canLoadTransferHistory || !officer) {
      return;
    }
    setTransferHistoryLoading(true);
    fetchOfficerTransferHistory(officerId, { pageSize: 3 })
      .then((result) => {
        setTransferHistory(result.items ?? []);
      })
      .catch(() => {
        setTransferHistory([]);
      })
      .finally(() => setTransferHistoryLoading(false));
  }, [officerId, canLoadTransferHistory, officer]);

  useEffect(() => {
    const ids = Array.from(
      new Set(
        transferHistory
          .map((item) => item.by)
          .filter((value): value is string => Boolean(value)),
      ),
    );
    if (!ids.length) {
      setTransferByMap({});
      return;
    }
    let isCurrent = true;
    Promise.all(
      ids.map(async (id) => ({
        id,
        meta: await fetchOfficerDisplayMetaById(id),
      })),
    )
      .then((items) => {
        if (!isCurrent) {
          return;
        }
        const nextMap: Record<string, { name: string | null; level: string | null }> = {};
        items.forEach((item) => {
          nextMap[item.id] = item.meta;
        });
        setTransferByMap(nextMap);
      })
      .catch(() => {
        if (!isCurrent) {
          return;
        }
        setTransferByMap({});
      });
    return () => {
      isCurrent = false;
    };
  }, [transferHistory]);

  const handleUpdate = async (values: OfficerUpdatePayload) => {
    if (!officerId) {
      return;
    }

    if (!canEdit) {
      return;
    }

    setUpdating(true);
    setError(null);
    try {
      const updated = await updateOfficer(officerId, values);
      setOfficer(updated);
      setIsEditing(false);
    } catch (err: any) {
      const message =
        mapErrorDetailToMessage(err?.response?.data?.detail) ??
        "ไม่สามารถบันทึกการแก้ไขได้ กรุณาตรวจสอบข้อมูล";
      setError(message);
    } finally {
      setUpdating(false);
    }
  };

  const requestToggleActive = () => {
    if (!officer || toggling || !canToggleActive) {
      return;
    }
    setConfirmState("toggle");
  };

  const requestApprove = () => {
    if (!officer || approving || rejecting || !canApprove) {
      return;
    }
    setConfirmState("approve");
  };

  const requestReject = () => {
    if (!officer || approving || rejecting || !canApprove) {
      return;
    }
    setConfirmState("reject");
  };

  const requestDelete = () => {
    if (!officer || !canDelete) {
      return;
    }
    setConfirmState("delete");
  };

  const requestPasswordReset = () => {
    if (!officer || !canResetPassword) {
      return;
    }
    setError(null);
    setTemporaryPassword(null);
    setCopiedTempPassword(false);
    setConfirmState("reset");
  };

  const requestTransfer = () => {
    if (!officer || !canTransfer) {
      return;
    }
    setTransferOpen(true);
  };

  const resetConfirmation = () => {
    if (
      toggling ||
      approving ||
      rejecting ||
      updating ||
      deleting ||
      resettingPassword
    ) {
      return;
    }
    setConfirmState(null);
  };

  const handleConfirmAction = async () => {
    if (!officer || !confirmState) {
      return;
    }

    if (confirmState === "toggle") {
      setToggling(true);
      setError(null);
      try {
        const updated = await setOfficerActiveStatus(
          officer.id,
          !officer.is_active,
        );
        setOfficer(updated);
        setConfirmState(null);
      } catch (err: any) {
        const message =
          mapErrorDetailToMessage(err?.response?.data?.detail) ??
          "ไม่สามารถเปลี่ยนสถานะได้ กรุณาลองใหม่";
        setError(message);
      } finally {
        setToggling(false);
      }
    } else if (confirmState === "approve") {
      setApproving(true);
      setError(null);
      try {
        const updated = await approveOfficer(officer.id);
        setOfficer(updated);
        setConfirmState(null);
      } catch (err: any) {
        const message =
          mapErrorDetailToMessage(err?.response?.data?.detail) ??
          "ไม่สามารถอนุมัติคำขอได้ กรุณาลองใหม่";
        setError(message);
      } finally {
        setApproving(false);
      }
    } else if (confirmState === "reject") {
      setRejecting(true);
      setError(null);
      try {
        const updated = await rejectOfficer(officer.id);
        setOfficer(updated);
        setConfirmState(null);
      } catch (err: any) {
        const message =
          mapErrorDetailToMessage(err?.response?.data?.detail) ??
          "ไม่สามารถปฏิเสธคำขอได้ กรุณาลองใหม่";
        setError(message);
      } finally {
        setRejecting(false);
      }
    } else if (confirmState === "delete") {
      setDeleting(true);
      try {
        await deleteOfficer(officer.id);
        setConfirmState(null);
        navigate(backToListPath);
      } catch (err: any) {
        const message =
          mapErrorDetailToMessage(err?.response?.data?.detail) ??
          "ไม่สามารถลบเจ้าหน้าที่ได้";
        setError(message);
      } finally {
        setDeleting(false);
      }
    } else if (confirmState === "reset") {
      setResettingPassword(true);
      setError(null);
      try {
        const result: OfficerPasswordResetResult = await resetOfficerPassword(
          officer.id,
        );
        setTemporaryPassword(result.temporary_password);
        setConfirmState(null);
      } catch (err: any) {
        const message =
          mapErrorDetailToMessage(err?.response?.data?.detail) ??
          err?.message ??
          "ไม่สามารถรีเซ็ตรหัสผ่านได้";
        setError(message);
      } finally {
        setResettingPassword(false);
      }
    }
  };

  const handleTransferSubmit = async (payload: OfficerTransferPayload) => {
    if (!officerId) {
      return;
    }
    setTransferBusy(true);
    setError(null);
    try {
      const updated = await transferOfficer(officerId, payload);
      setOfficer(updated);
      setTransferOpen(false);
      const history = await fetchOfficerTransferHistory(officerId);
      setTransferHistory(history.items ?? []);
    } catch (err: any) {
      const message =
        mapErrorDetailToMessage(err?.response?.data?.detail) ??
        "ไม่สามารถโยกย้ายเจ้าหน้าที่ได้ กรุณาลองใหม่";
      setError(message);
    } finally {
      setTransferBusy(false);
    }
  };

  const handleCopyTemporaryPassword = async () => {
    if (!temporaryPassword) {
      return;
    }
    try {
      await navigator.clipboard.writeText(temporaryPassword);
      setCopiedTempPassword(true);
      window.setTimeout(() => setCopiedTempPassword(false), 2000);
    } catch (err) {
      setCopiedTempPassword(false);
    }
  };

  if (loading) {
    return (
      <div className="py-6">
        <PageLoader minHeight={360} message="กำลังโหลดข้อมูลเจ้าหน้าที่" />
      </div>
    );
  }

  if (!officer) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        <p className="text-sm font-semibold">ไม่พบข้อมูลเจ้าหน้าที่</p>
        <Link
          to={backToListPath}
          className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-rose-700 underline"
        >
          ← กลับไปยังรายการ
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-6 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-blue-600">
              Officer Detail
            </p>
            <h1 className="text-2xl font-bold text-slate-900">
              {officer.first_name} {officer.last_name}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-600">
              <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
                <span>Citizen ID</span>
                <SensitiveValue
                  value={officer.citizen_id}
                  className="inline-flex items-center gap-1"
                  valueClassName="font-mono text-xs uppercase tracking-wide text-slate-700"
                  buttonClassName="rounded-full border border-slate-200 p-1 text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
                  revealIcon={<EyeIcon />}
                  hideIcon={<EyeOffIcon />}
                />
              </span>
              <span
                className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                  officer.is_active
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-rose-100 text-rose-700"
                }`}
              >
                {officer.is_active ? "เปิดใช้งาน" : "ปิดใช้งาน"}
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-blue-600">
                {officer.approval_status}
              </span>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Link
              to={backToListPath}
              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
            >
              ← กลับไปยังรายการ
            </Link>
            {canEdit && (
              <button
                type="button"
                onClick={() => setIsEditing((value) => !value)}
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-4 py-2 text-sm font-semibold text-blue-600 transition hover:border-blue-300 hover:bg-blue-50"
              >
                {isEditing ? "ยกเลิก" : "แก้ไข"}
              </button>
            )}
            {canApprove && officer.approval_status === "pending" && (
              <>
                <button
                  type="button"
                  onClick={requestApprove}
                  disabled={approving || rejecting || toggling || deleting}
                  className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-4 py-2 text-sm font-semibold text-emerald-600 transition hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  อนุมัติ
                </button>
                <button
                  type="button"
                  onClick={requestReject}
                  disabled={approving || rejecting || toggling || deleting}
                  className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-4 py-2 text-sm font-semibold text-amber-600 transition hover:border-amber-300 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  ปฏิเสธ
                </button>
              </>
            )}
            {canToggleActive && officer.approval_status === "approved" && (
              <button
                type="button"
                onClick={requestToggleActive}
                disabled={toggling || deleting}
                className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 px-4 py-2 text-sm font-semibold text-emerald-600 transition hover:border-emerald-300 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {officer.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
              </button>
            )}
            {canResetPassword && (
              <button
                type="button"
                onClick={requestPasswordReset}
                disabled={resettingPassword || toggling || deleting}
                className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-4 py-2 text-sm font-semibold text-amber-600 transition hover:border-amber-300 hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                รีเซ็ตรหัสผ่าน
              </button>
            )}
            {showTransferButton && (
              <button
                type="button"
                onClick={requestTransfer}
                disabled={transferBusy || toggling || deleting}
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-4 py-2 text-sm font-semibold text-blue-600 transition hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                โยกย้าย
              </button>
            )}
            {canDelete && (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-600 transition hover:border-rose-300 hover:bg-rose-50"
                onClick={requestDelete}
                disabled={deleting || toggling}
              >
                ลบบัญชี
              </button>
            )}
          </div>
        </div>
      </header>

      {showPeerRestrictionNotice && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 shadow-inner">
          คุณมีสิทธิ์ระดับเดียวกันกับเจ้าหน้าที่คนนี้จึงไม่สามารถจัดการบัญชีได้
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-inner">
          {error}
        </div>
      )}

      {temporaryPassword && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 shadow-inner">
          <p className="font-semibold">
            สร้างรหัสผ่านชั่วคราวใหม่ให้ผู้ใช้งานแล้ว
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <code className="rounded-lg bg-white px-3 py-2 text-base font-semibold tracking-wide text-amber-700 shadow">
              {temporaryPassword}
            </code>
            <button
              type="button"
              onClick={handleCopyTemporaryPassword}
              className="inline-flex items-center justify-center rounded-lg border border-amber-300 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-700 transition hover:border-amber-400 hover:bg-amber-100"
            >
              {copiedTempPassword ? "คัดลอกแล้ว" : "คัดลอกรหัสผ่าน"}
            </button>
          </div>
          <p className="mt-2 text-xs text-amber-600">
            โปรดส่งต่อรหัสผ่านนี้และให้เจ้าหน้าที่เปลี่ยนรหัสผ่านใหม่ทันทีหลังเข้าสู่ระบบ
          </p>
        </div>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {isEditing ? (
          <OfficerForm
            mode="edit"
            initialValues={officer}
            onSubmit={handleUpdate}
            isSubmitting={updating}
            submitLabel="บันทึกการแก้ไข"
          />
        ) : (
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">
                ข้อมูลติดต่อ
              </h2>
              <dl className="space-y-3">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    เลขบัตรประชาชน
                  </dt>
                  <dd className="text-sm text-slate-800">
                    <SensitiveValue
                      value={officer.citizen_id}
                      className="inline-flex items-center gap-2"
                      valueClassName="font-mono text-sm text-slate-800"
                      buttonClassName="rounded-full border border-slate-200 p-1 text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
                      revealIcon={<EyeIcon />}
                      hideIcon={<EyeOffIcon />}
                    />
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    อีเมล
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.email ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    เบอร์โทรศัพท์
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.phone ?? "-"}
                  </dd>
                </div>
              </dl>
            </div>
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">
                ตำแหน่งและพื้นที่
              </h2>
              <dl className="space-y-3">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    ตำแหน่ง
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.position_name_th ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    เขตสุขภาพ
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.health_area_name_th ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    จังหวัด
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.province_name_th ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    อำเภอ
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.district_name_th ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    ตำบล
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.subdistrict_name_th ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    หน่วยบริการสุขภาพ
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.health_service_name_th ?? "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    ประเภทพื้นที่
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {renderAreaType(officer.area_type)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    รหัสพื้นที่
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {officer.area_code ?? "-"}
                  </dd>
                </div>
              </dl>
            </div>
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-slate-900">
                ข้อมูลระบบ
              </h2>
              <dl className="space-y-3">
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    สถานะการอนุมัติ
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {APPROVAL_STATUS_LABELS[officer.approval_status] ??
                      officer.approval_status}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    สร้างเมื่อ
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {formatBangkokDateTime(officer.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    แก้ไขล่าสุด
                  </dt>
                  <dd className="text-sm text-slate-800">
                    {formatBangkokDateTime(officer.updated_at)}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">
          ประวัติการโยกย้าย
        </h2>
        {transferHistoryLoading ? (
          <div className="mt-4 text-sm text-slate-500">กำลังโหลดประวัติ…</div>
        ) : transferHistory.length === 0 ? (
          <div className="mt-4 text-sm text-slate-500">
            ยังไม่มีประวัติการโยกย้าย
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {transferHistory.map((item) => (
              
              <div
                key={item.id}
                className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-700"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">
                    {item.description?.includes("Transferred officer")
                      ? "โยกย้ายเจ้าหน้าที่"
                      : (item.description ?? "โยกย้ายเจ้าหน้าที่")}
                  </span>
                  <span className="text-xs text-slate-500">
                    {formatBangkokDateTime(item.timestamp)}
                  </span>
                </div>
                <div className="mt-2 text-xs text-slate-500">
                  {(() => {
                    const actor = item.by ? transferByMap[item.by] : null;
                    const actorName = actor?.name ?? "-";
                    const actorLevel = actor?.level;
                    const actorLevelLabel = actorLevel
                      ? (AREA_TYPE_LABELS[actorLevel as AdministrativeLevel] ?? actorLevel)
                      : null;
                    return (
                      <>
                        ผู้ดำเนินการ: {actorName}
                        {actorLevelLabel ? ` (${actorLevelLabel})` : ""}
                      </>
                    );
                  })()}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  จาก: {renderTransferLocation(item.old_data)}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  ไป: {renderTransferLocation(item.new_data)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <OfficerTransferDialog
        open={transferOpen}
        officer={officer}
        onClose={() => {
          if (transferBusy) {
            return;
          }
          setTransferOpen(false);
        }}
        onSubmit={handleTransferSubmit}
        busy={transferBusy}
      />

      <ConfirmDialog
        open={Boolean(confirmState)}
        title={
          confirmState === "delete"
            ? "ยืนยันการลบบัญชี"
            : confirmState === "reset"
              ? "ยืนยันการรีเซ็ตรหัสผ่าน"
              : confirmState === "approve"
                ? "ยืนยันการอนุมัติ"
                : confirmState === "reject"
                  ? "ยืนยันการปฏิเสธ"
                  : "ยืนยันการเปลี่ยนสถานะ"
        }
        message={
          confirmState === "delete"
            ? `การลบบัญชีของ ${officer.first_name} ${officer.last_name} เป็นการดำเนินการแบบถาวร\nระบบจะลบสิทธิ์การเข้าถึงทั้งหมด ไม่สามารถกู้คืนได้\nต้องการดำเนินการต่อหรือไม่?`
            : confirmState === "reset"
              ? `ระบบจะสร้างรหัสผ่านชั่วคราวใหม่ให้ ${officer.first_name} ${officer.last_name}\nรหัสผ่านเดิมทั้งหมดจะไม่สามารถใช้งานได้ทันที\nต้องการดำเนินการต่อหรือไม่?`
              : confirmState === "approve"
                ? `ต้องการอนุมัติคำขอของ ${officer.first_name} ${officer.last_name} หรือไม่?\nระบบจะเปิดใช้งานบัญชีให้ทันที`
                : confirmState === "reject"
                  ? `ต้องการปฏิเสธคำขอของ ${officer.first_name} ${officer.last_name} หรือไม่?\nผู้สมัครจะไม่สามารถเข้าระบบได้จนกว่าจะสมัครใหม่`
                  : `ต้องการ${
                      officer.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"
                    }บัญชีของ ${officer.first_name} ${
                      officer.last_name
                    } หรือไม่?\nคุณสามารถเปลี่ยนสถานะได้อีกครั้งภายหลัง`
        }
        confirmLabel={
          confirmState === "delete"
            ? "ลบบัญชี"
            : confirmState === "reset"
              ? "รีเซ็ตรหัสผ่าน"
              : confirmState === "approve"
                ? "อนุมัติ"
                : confirmState === "reject"
                  ? "ปฏิเสธ"
                  : officer.is_active
                    ? "ปิดใช้งาน"
                    : "เปิดใช้งาน"
        }
        cancelLabel="ยกเลิก"
        variant={
          confirmState === "delete" || confirmState === "reject"
            ? "danger"
            : "default"
        }
        onCancel={resetConfirmation}
        onConfirm={handleConfirmAction}
        busy={
          confirmState === "toggle"
            ? toggling
            : confirmState === "approve"
              ? approving
              : confirmState === "reject"
                ? rejecting
                : confirmState === "delete"
                  ? deleting
                  : confirmState === "reset"
                    ? resettingPassword
                    : false
        }
      />
    </div>
  );
};

export default OfficerDetailPage;
