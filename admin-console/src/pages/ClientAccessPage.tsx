import React, {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  fetchOAuthClients,
  updateOAuthClientUserTypes,
  resetOAuthClientUserTypesToDefault,
  createOAuthClient,
  updateOAuthClient,
} from "../api/oauthClients";
import {
  OAuthClientSummary,
  UpdateClientUserTypesPayload,
  UserType,
  CreateOAuthClientPayload,
  UpdateOAuthClientPayload,
} from "../types/oauthClient";
import { useAuth } from "../hooks/useAuth";
import { canManageClientAccess } from "../utils/permissions";
import { ClientBlockManager } from "../components/ClientBlockManager";
import { PageLoader } from "../components/ui/PageLoader";

type ScopeOption = {
  value: string;
  label: string;
  description?: string;
  defaultSelected?: boolean;
};
type ScopeGroup = { title: string; helper?: string; options: ScopeOption[] };

type GrantOption = {
  value: string;
  label: string;
  helper?: string;
  defaultSelected?: boolean;
};
type GrantGroup = { title: string; helper?: string; options: GrantOption[] };

const USER_TYPE_OPTIONS: {
  value: UserType;
  label: string;
  readOnly?: boolean;
}[] = [
  { value: "officer", label: "Officer" },
  { value: "osm", label: "OSM" },
  { value: "yuwa_osm", label: "Yuwa OSM" },
  { value: "people", label: "People" },
  { value: "gen_h", label: "GenH" },
];

/** Editable user types — used for bulk actions (allow-all / disallow-all). */
const ALL_USER_TYPES: UserType[] = USER_TYPE_OPTIONS.filter(
  (o) => !o.readOnly
).map((o) => o.value);

const SCOPE_GROUPS: ScopeGroup[] = [
  {
    title: "ข้อมูลจำเป็นสำหรับการยืนยันตัวตน",
    helper: "ระบบกำหนดให้เลือกไว้ล่วงหน้าเพื่อรองรับขั้นตอน OAuth มาตรฐาน",
    options: [
      {
        value: "openid",
        label: "openid",
        description: "จำเป็นสำหรับการแลก user info",
        defaultSelected: true,
      },
      {
        value: "profile",
        label: "profile",
        description: "ชื่อ-สกุล และข้อมูลโปรไฟล์พื้นฐาน",
        defaultSelected: true,
      },
    ],
  },
  {
    title: "ข้อมูลส่วนบุคคลเพิ่มเติม",
    helper: "เลือกเฉพาะเมื่อระบบปลายทางจำเป็นต้องเปิดเผยข้อมูลเพิ่ม",
    options: [
      { value: "email", label: "email", description: "อีเมลสำหรับการติดต่อ" },
      { value: "phone", label: "phone", description: "หมายเลขโทรศัพท์" },
      { value: "gender", label: "gender", description: "เพศของผู้ใช้งาน" },
      {
        value: "address",
        label: "address",
        description: "ที่อยู่ตามทะเบียนบ้าน",
      },
      {
        value: "birth_date",
        label: "birth_date",
        description: "วันเดือนปีเกิด",
      },
    ],
  },
];

const GRANT_TYPE_GROUPS: GrantGroup[] = [
  {
    title: "รูปแบบเข้าสู่ระบบ",
    helper: "เลือกช่องทางที่ผู้ใช้จะใช้ login เพื่อรับโทเคน",
    options: [
      {
        value: "authorization_code",
        label: "Authorization Code",
        helper: "เหมาะสำหรับเว็บหรือ confidential client",
        defaultSelected: true,
      },
      {
        value: "direct_login",
        label: "Direct Login",
        helper: "รองรับ mobile/SPA ใช้ citizen id",
        defaultSelected: true,
      },
    ],
  },
  {
    title: "การต่ออายุเซสชัน",
    helper: "เปิดหาก client ต้องต่ออายุ token แบบ background",
    options: [
      {
        value: "refresh_token",
        label: "Refresh Token",
        helper: "ใช้สำหรับต่ออายุ session",
        defaultSelected: true,
      },
    ],
  },
];

const FLAT_SCOPE_OPTIONS = SCOPE_GROUPS.flatMap((group) => group.options);
const DEFAULT_SCOPE_VALUES = FLAT_SCOPE_OPTIONS.filter(
  (option) => option.defaultSelected
).map((option) => option.value);

const FLAT_GRANT_OPTIONS = GRANT_TYPE_GROUPS.flatMap((group) => group.options);
const DEFAULT_GRANT_TYPES = FLAT_GRANT_OPTIONS.filter(
  (option) => option.defaultSelected !== false
).map((option) => option.value);

const ERROR_FIELD_TO_ELEMENT_ID: Record<string, string> = {
  client_name: "client-name-input",
  redirect_uri: "redirect-uri-input",
  login_url: "login-url-input",
  consent_url: "consent-url-input",
  scopes: "scopes-section",
  grant_types: "grant-types-section",
};

const CLIENT_FORM_ALERT_ID = "client-form-alert";

type ClientFormState = Omit<CreateOAuthClientPayload, "client_description"> & {
  client_description: string;
};

const createDefaultClientForm = (): ClientFormState => ({
  client_name: "",
  client_description: "",
  redirect_uri: "",
  login_url: "",
  consent_url: "",
  scopes: [...DEFAULT_SCOPE_VALUES],
  grant_types: [...DEFAULT_GRANT_TYPES],
  public_client: true,
});

const formatUrlHost = (url: string): string => {
  try {
    const parsed = new URL(url);
    return parsed.origin;
  } catch (_error) {
    return url;
  }
};

const InfoTooltip = ({
  label,
  tooltip,
}: {
  label: string;
  tooltip: string;
}) => (
  <span
    className="ml-2 inline-flex cursor-help items-center rounded-full border border-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-500 hover:border-slate-300 hover:text-slate-600"
    title={tooltip}
  >
    {label}
  </span>
);

type IconProps = { className?: string };

const IconEdit = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M4 20h4l11-11-4-4L4 16v4z" />
    <path d="M13 5l4 4" />
  </svg>
);

const IconSave = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="8.5" />
    <path d="M8.5 12.5l2.5 2.5 4.5-5" />
  </svg>
);

const IconShield = ({ className = "h-5 w-5" }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    aria-hidden="true"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth={1.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3l7 3v5c0 5-3.5 9.5-7 10-3.5-.5-7-5-7-10V6l7-3z" />
    <path d="M9 14l6-6" />
  </svg>
);

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
      d="M21 12a9 9 0 00-9-9"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
    />
  </svg>
);

type IconButtonProps = {
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "ghost" | "primary" | "muted";
  active?: boolean;
  children: React.ReactNode;
};

const IconButton: React.FC<IconButtonProps> = ({
  label,
  onClick,
  disabled = false,
  variant = "ghost",
  active = false,
  children,
}) => {
  const baseClass =
    "inline-flex h-9 w-9 items-center justify-center rounded-lg border text-sm transition focus:outline-none focus:ring-2 focus:ring-blue-100 focus:ring-offset-1";
  const variantClass =
    variant === "primary"
      ? "border-transparent bg-blue-600 text-white hover:bg-blue-700"
      : variant === "muted"
      ? "border-slate-200 bg-slate-100 text-slate-400"
      : "border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100";
  const activeClass =
    active && !disabled ? "border-blue-200 bg-blue-50 text-blue-600" : "";
  const disabledClass = disabled ? "cursor-not-allowed opacity-50" : "";

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`${baseClass} ${variantClass} ${activeClass} ${disabledClass}`.trim()}
      disabled={disabled}
    >
      {children}
      <span className="sr-only">{label}</span>
    </button>
  );
};

export const ClientAccessPage: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [items, setItems] = useState<OAuthClientSummary[]>([]);
  const [original, setOriginal] = useState<Record<string, UserType[] | null>>(
    {}
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingMap, setSavingMap] = useState<Record<string, boolean>>({});
  const [expandedClientId, setExpandedClientId] = useState<string | null>(null);
  const hasFetchedRef = useRef(false);
  const [resettingMap, setResettingMap] = useState<Record<string, boolean>>(
    {}
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isModalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editingClientId, setEditingClientId] = useState<string | null>(null);
  const [clientForm, setClientForm] = useState<ClientFormState>(
    createDefaultClientForm
  );
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [isSubmittingClient, setIsSubmittingClient] = useState(false);
  const [formSubmitError, setFormSubmitError] = useState<string | null>(null);

  const handleClientUpdated = useCallback((updated: OAuthClientSummary) => {
    setItems((prev) =>
      prev.map((client) =>
        client.client_id === updated.client_id ? updated : client
      )
    );
    setOriginal((prev) => ({
      ...prev,
      [updated.client_id]: updated.allowed_user_types,
    }));
  }, []);

  const isAdmin = canManageClientAccess(user);

  const resetClientFormState = () => {
    setClientForm(createDefaultClientForm());
    setFormErrors({});
    setFormSubmitError(null);
    setEditingClientId(null);
    setModalMode("create");
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchOAuthClients();
      setItems(response);
      const nextOriginal: Record<string, UserType[] | null> = {};
      response.forEach((client) => {
        nextOriginal[client.client_id] = client.allowed_user_types;
      });
      setOriginal(nextOriginal);
    } catch (err: any) {
      setError(err?.message ?? "ไม่สามารถดึงข้อมูลได้");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (!isAdmin) {
      setLoading(false);
      return;
    }
    if (hasFetchedRef.current) {
      return;
    }
    hasFetchedRef.current = true;
    load();
  }, [isAdmin, isLoading, load]);

  /** Read-only types that the current client already has — preserved across edits. */
  const readOnlyTypes = new Set(
    USER_TYPE_OPTIONS.filter((o) => o.readOnly).map((o) => o.value)
  );
  const preserveReadOnly = (client: OAuthClientSummary, next: UserType[]) => {
    const kept = (client.allowed_user_types ?? []).filter((t) =>
      readOnlyTypes.has(t)
    );
    return [...new Set([...next, ...kept])];
  };

  const toggleUserType = (clientId: string, userType: UserType) => {
    if (readOnlyTypes.has(userType)) return;
    setItems((prev) =>
      prev.map((client) => {
        if (client.client_id !== clientId) {
          return client;
        }
        const base = client.allowed_user_types ?? [];
        const set = new Set<UserType>(base);
        if (set.has(userType)) {
          set.delete(userType);
        } else {
          set.add(userType);
        }
        const nextList = ALL_USER_TYPES.filter((value) => set.has(value));
        return {
          ...client,
          allowed_user_types: preserveReadOnly(client, nextList),
        };
      })
    );
  };

  const handleAllowAll = (clientId: string) => {
    setItems((prev) =>
      prev.map((client) =>
        client.client_id === clientId
          ? {
              ...client,
              allowed_user_types: preserveReadOnly(client, [
                ...ALL_USER_TYPES,
              ]),
            }
          : client
      )
    );
  };

  const handleDisallowAll = (clientId: string) => {
    setItems((prev) =>
      prev.map((client) =>
        client.client_id === clientId
          ? {
              ...client,
              allowed_user_types: preserveReadOnly(client, []),
            }
          : client
      )
    );
  };

  const handleReset = (clientId: string) => {
    setItems((prev) =>
      prev.map((client) =>
        client.client_id === clientId
          ? { ...client, allowed_user_types: original[clientId] ?? null }
          : client
      )
    );
  };

  const handleResetToDefault = async (client: OAuthClientSummary) => {
    setResettingMap((prev) => ({ ...prev, [client.client_id]: true }));
    try {
      const updated = await resetOAuthClientUserTypesToDefault(
        client.client_id
      );
      setItems((prev) =>
        prev.map((item) =>
          item.client_id === client.client_id ? updated : item
        )
      );
      setOriginal((prev) => ({
        ...prev,
        [client.client_id]: updated.allowed_user_types,
      }));
      setError(null);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ?? err?.message ?? "คืนค่าเริ่มต้นไม่สำเร็จ"
      );
    } finally {
      setResettingMap((prev) => ({ ...prev, [client.client_id]: false }));
    }
  };

  const isDirty = useCallback(
    (client: OAuthClientSummary) => {
      const originalSelection = original[client.client_id];
      const currentSelection = client.allowed_user_types;
      const normalize = (values: UserType[] | null | undefined) => {
        if (values == null) {
          return "__DEFAULT__";
        }
        const set = new Set(values);
        return ALL_USER_TYPES.filter((item) => set.has(item)).join(",");
      };
      return normalize(originalSelection) !== normalize(currentSelection);
    },
    [original]
  );

  const toggleBlocks = (clientId: string) => {
    setExpandedClientId((prev) => (prev === clientId ? null : clientId));
  };

  const handleSave = async (client: OAuthClientSummary) => {
    const selection = client.allowed_user_types;
    const payload: UpdateClientUserTypesPayload = {
      allowed_user_types: selection == null ? null : [...selection],
    };
    setSavingMap((prev) => ({ ...prev, [client.client_id]: true }));
    try {
      const updated = await updateOAuthClientUserTypes(
        client.client_id,
        payload
      );
      setItems((prev) =>
        prev.map((item) =>
          item.client_id === client.client_id ? updated : item
        )
      );
      setOriginal((prev) => ({
        ...prev,
        [client.client_id]: updated.allowed_user_types,
      }));
      setError(null);
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ?? err?.message ?? "บันทึกไม่สำเร็จ"
      );
    } finally {
      setSavingMap((prev) => ({ ...prev, [client.client_id]: false }));
    }
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) =>
      a.client_name.localeCompare(b.client_name)
    );
  }, [items]);

  const openCreateModal = () => {
    resetClientFormState();
    setModalOpen(true);
  };

  const openEditModal = (client: OAuthClientSummary) => {
    setModalMode("edit");
    setEditingClientId(client.client_id);
    setClientForm({
      client_name: client.client_name,
      client_description: client.client_description ?? "",
      redirect_uri: client.redirect_uri,
      login_url: client.login_url ?? "",
      consent_url: client.consent_url ?? "",
      scopes: [...(client.scopes ?? [])],
      grant_types: [...(client.grant_types ?? [])],
      public_client: client.public_client,
    });
    setFormErrors({});
    setFormSubmitError(null);
    setModalOpen(true);
  };

  const closeModal = () => {
    if (!isSubmittingClient) {
      setModalOpen(false);
      resetClientFormState();
    }
  };

  const focusElementById = (elementId?: string | null) => {
    if (!elementId || typeof document === "undefined") {
      return;
    }
    requestAnimationFrame(() => {
      const element = document.getElementById(elementId);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
        if (element instanceof HTMLElement) {
          element.focus({ preventScroll: true });
        }
      }
    });
  };

  const focusValidationTarget = (errorKey: string | null) => {
    if (errorKey) {
      const targetId = ERROR_FIELD_TO_ELEMENT_ID[errorKey];
      if (targetId) {
        focusElementById(targetId);
        return;
      }
    }
    focusElementById(CLIENT_FORM_ALERT_ID);
  };

  const toggleScope = (value: string) => {
    setClientForm((prev) => {
      const set = new Set(prev.scopes);
      if (set.has(value)) {
        set.delete(value);
      } else {
        set.add(value);
      }
      return { ...prev, scopes: Array.from(set) };
    });
  };

  const toggleGrantType = (value: string) => {
    setClientForm((prev) => {
      const set = new Set(prev.grant_types);
      if (set.has(value)) {
        set.delete(value);
      } else {
        set.add(value);
      }
      const next = Array.from(set);
      return { ...prev, grant_types: next.length ? next : [value] };
    });
  };

  const validateClientPayload = (
    scopes: string[],
    grantTypes: string[]
  ): { isValid: boolean; firstErrorKey: string | null } => {
    const nextErrors: Record<string, string> = {};
    let firstErrorKey: string | null = null;

    const registerError = (key: string, message: string) => {
      if (!firstErrorKey) {
        firstErrorKey = key;
      }
      nextErrors[key] = message;
    };

    if (!clientForm.client_name.trim()) {
      registerError("client_name", "กรุณาระบุชื่อ Project");
    }
    if (!clientForm.redirect_uri.trim()) {
      registerError("redirect_uri", "ต้องระบุ Redirect URI");
    }
    if (!clientForm.login_url.trim()) {
      registerError("login_url", "ต้องระบุ Login URL");
    }
    if (!clientForm.consent_url.trim()) {
      registerError("consent_url", "ต้องระบุ Consent URL");
    }
    if (scopes.length === 0) {
      registerError("scopes", "ต้องเลือก Scope อย่างน้อย 1 ค่า");
    }
    if (grantTypes.length === 0) {
      registerError("grant_types", "ต้องเลือก Grant Type อย่างน้อย 1 ค่า");
    }

    setFormErrors(nextErrors);
    return { isValid: Object.keys(nextErrors).length === 0, firstErrorKey };
  };

  const handleClientSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedScopes = Array.from(
      new Set(
        clientForm.scopes
          .map((scope) => scope.trim())
          .filter((scope) => scope.length > 0)
      )
    );
    const grantTypes = clientForm.grant_types.length
      ? Array.from(new Set(clientForm.grant_types))
      : FLAT_GRANT_OPTIONS.map((option) => option.value);

    const validationResult = validateClientPayload(
      normalizedScopes,
      grantTypes
    );
    if (!validationResult.isValid) {
      setFormSubmitError(
        "กรุณากรอกข้อมูลให้ครบถ้วนหรือแก้ไขช่องที่มีแจ้งเตือนก่อนบันทึก Project"
      );
      focusValidationTarget(validationResult.firstErrorKey);
      return;
    }

    setFormSubmitError(null);
    setIsSubmittingClient(true);

    const basePayload = {
      ...clientForm,
      scopes: normalizedScopes,
      grant_types: grantTypes,
      client_description: clientForm.client_description.trim(),
    };

    try {
      if (modalMode === "create") {
        const payload: CreateOAuthClientPayload = {
          ...basePayload,
          client_description: basePayload.client_description || undefined,
        };
        const created = await createOAuthClient(payload);
        setItems((prev) => [...prev, created]);
        setOriginal((prev) => ({
          ...prev,
          [created.client_id]: created.allowed_user_types,
        }));
        setSuccessMessage(`สร้าง Project ${created.client_name} เรียบร้อยแล้ว`);
      } else if (editingClientId) {
        const payload: UpdateOAuthClientPayload = {
          ...basePayload,
          client_description: basePayload.client_description || undefined,
        };
        const updated = await updateOAuthClient(editingClientId, payload);
        setItems((prev) =>
          prev.map((item) =>
            item.client_id === updated.client_id ? updated : item
          )
        );
        setOriginal((prev) => ({
          ...prev,
          [updated.client_id]: updated.allowed_user_types,
        }));
        setSuccessMessage(
          `อัปเดต Project ${updated.client_name} เรียบร้อยแล้ว`
        );
      }
      resetClientFormState();
      setModalOpen(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const fallbackMessage =
        modalMode === "create"
          ? "ไม่สามารถสร้าง Project ได้"
          : "ไม่สามารถบันทึก Project ได้";
      setFormSubmitError(
        typeof detail === "string" ? detail : err?.message ?? fallbackMessage
      );
      focusElementById(CLIENT_FORM_ALERT_ID);
    } finally {
      setIsSubmittingClient(false);
    }
  };

  if (isLoading || loading) {
    return (
      <div className="py-6">
        <PageLoader message="กำลังโหลดข้อมูลการเข้าถึงระบบ" />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-4xl">
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center">
          <h2 className="text-lg font-semibold text-amber-800">
            ไม่มีสิทธิ์เข้าถึง
          </h2>
          <p className="mt-2 text-sm text-amber-700">
            ฟีเจอร์นี้สำหรับผู้ดูแลระบบเท่านั้น
          </p>
        </div>
      </div>
    );
  }

  const canCreateClient = isAdmin;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            กำหนดสิทธิ์การเข้าถึงระบบหน้าบ้าน
          </h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            เลือกประเภทผู้ใช้ที่อนุญาตให้ล็อกอินได้ต่อ OAuth Client แต่ละตัว
            หากไม่ได้เลือกเลยถือว่าไม่อนุญาตให้เข้าระบบ ปุ่ม "อนุญาตทุกประเภท"
            จะล้างข้อกำหนดและใช้ค่ามาตรฐาน
          </p>
        </div>
        {canCreateClient && (
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700"
          >
            + สร้าง Project ใหม่
          </button>
        )}
      </div>

      {successMessage && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 shadow-inner">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Client
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                Redirect / Domain
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                ประเภทผู้ใช้ที่อนุญาต
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                การทำงาน
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {sortedItems.map((client) => {
              const selected = new Set<UserType>(
                client.allowed_user_types ?? []
              );
              const dirty = isDirty(client);
              const isSaving = savingMap[client.client_id] ?? false;
              const isResetting = resettingMap[client.client_id] ?? false;
              const expanded = expandedClientId === client.client_id;
              return (
                <React.Fragment key={client.client_id}>
                  <tr className="hover:bg-slate-50">
                    <td className="px-4 py-4 align-top">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-900">
                          {client.client_name}
                        </span>
                        {client.allowlist_enabled ? (
                          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700 border border-amber-200">
                            Allow Mode
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-500 border border-slate-200">
                            Block Mode
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-500">
                        {client.client_id}
                      </div>
                      {client.client_description && (
                        <div className="mt-1 text-xs text-slate-500">
                          {client.client_description}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="text-sm text-slate-700">
                        {formatUrlHost(client.redirect_uri)}
                      </div>
                      {client.login_url && (
                        <div className="text-xs text-slate-400 break-all">
                          Login base: {client.login_url}
                          {(client.login_url_example || client.login_url) && (
                            <InfoTooltip
                              label="ดูตัวอย่าง"
                              tooltip={
                                client.login_url_example ?? client.login_url
                              }
                            />
                          )}
                        </div>
                      )}
                      {client.consent_url && (
                        <div className="text-xs text-slate-400 break-all">
                          Consent base: {client.consent_url}
                          {(client.consent_url_example ||
                            client.consent_url) && (
                            <InfoTooltip
                              label="ดูตัวอย่าง"
                              tooltip={
                                client.consent_url_example ?? client.consent_url
                              }
                            />
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4 align-top">
                      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                        {USER_TYPE_OPTIONS.map((option) => (
                          <label
                            key={option.value}
                            className={`inline-flex items-center gap-2 text-sm ${
                              option.readOnly
                                ? "text-slate-400 cursor-not-allowed"
                                : "text-slate-700"
                            }`}
                            title={
                              option.readOnly
                                ? "จัดการได้ผ่านฐานข้อมูลเท่านั้น"
                                : undefined
                            }
                          >
                            <input
                              type="checkbox"
                              className={`h-4 w-4 rounded border-slate-300 focus:ring-blue-500 ${
                                option.readOnly
                                  ? "text-slate-400 cursor-not-allowed"
                                  : "text-blue-600"
                              }`}
                              checked={selected.has(option.value)}
                              disabled={option.readOnly}
                              onChange={() =>
                                toggleUserType(client.client_id, option.value)
                              }
                            />
                            <span>{option.label}</span>
                            {option.readOnly && (
                              <svg
                                className="h-3.5 w-3.5 text-slate-400"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth={2}
                                stroke="currentColor"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
                                />
                              </svg>
                            )}
                          </label>
                        ))}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs">
                        <button
                          className="rounded-full border border-blue-100 px-3 py-1 text-blue-600 transition hover:border-blue-200 hover:bg-blue-50"
                          onClick={() => handleAllowAll(client.client_id)}
                          type="button"
                        >
                          อนุญาตทุกประเภท
                        </button>
                        <button
                          className="rounded-full border border-amber-100 px-3 py-1 text-amber-600 transition hover:border-amber-200 hover:bg-amber-50"
                          onClick={() => handleDisallowAll(client.client_id)}
                          type="button"
                        >
                          ห้ามทั้งหมด
                        </button>
                        <button
                          className="rounded-full border border-slate-200 px-3 py-1 text-slate-500 transition hover:border-slate-300 hover:bg-slate-100"
                          onClick={() => handleReset(client.client_id)}
                          type="button"
                          disabled={!dirty}
                        >
                          ย้อนกลับ
                        </button>
                        <button
                          className="rounded-full border border-emerald-100 px-3 py-1 text-emerald-600 transition hover:border-emerald-200 hover:bg-emerald-50"
                          onClick={() => handleResetToDefault(client)}
                          type="button"
                          disabled={isResetting}
                        >
                          ค่าเริ่มต้น
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right align-top">
                      <div className="flex items-center justify-end gap-2">
                        <IconButton
                          label="แก้ไขรายละเอียด"
                          onClick={() => openEditModal(client)}
                        >
                          <IconEdit />
                        </IconButton>
                        <IconButton
                          label={
                            dirty
                              ? "บันทึกการเปลี่ยนแปลง"
                              : "ไม่มีการเปลี่ยนแปลง"
                          }
                          onClick={() => handleSave(client)}
                          disabled={!dirty || isSaving}
                          variant={dirty ? "primary" : "muted"}
                        >
                          {isSaving ? (
                            <IconSpinner className="h-5 w-5 text-white" />
                          ) : (
                            <IconSave className="h-5 w-5" />
                          )}
                        </IconButton>
                        <IconButton
                          label={expanded ? "ซ่อนการบล็อก" : "จัดการการบล็อก"}
                          onClick={() => toggleBlocks(client.client_id)}
                          active={expanded}
                        >
                          <IconShield
                            className={`h-5 w-5 ${
                              client.allowlist_enabled
                                ? "text-amber-500"
                                : ""
                            }`}
                          />
                        </IconButton>
                      </div>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="bg-slate-50">
                      <td colSpan={4} className="border-t border-slate-200">
                        <ClientBlockManager
                          client={client}
                          onClientUpdated={handleClientUpdated}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
            {sortedItems.length === 0 && (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-12 text-center text-sm text-slate-500"
                >
                  ไม่พบบัญชี OAuth Client
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-slate-900/40 px-4 py-10 backdrop-blur-sm">
          <div className="w-full max-w-3xl rounded-2xl bg-white shadow-2xl">
            <form
              onSubmit={handleClientSubmit}
              className="space-y-6"
              noValidate
            >
              <div className="flex items-start justify-between border-b border-slate-200 px-6 py-5">
                <div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    {modalMode === "create"
                      ? "สร้าง Project ใหม่"
                      : "แก้ไขข้อมูล Project"}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {modalMode === "create"
                      ? "เมื่อสร้างแล้วระบบจะออก client_id ใหม่ให้สำหรับเชื่อมต่อบริการหน้าบ้าน โปรดเก็บข้อมูล client ที่ได้รับไว้ใช้งาน"
                      : "ปรับปรุงรายละเอียดการเชื่อมต่อและสิทธิ์ของ Project ได้จากหน้านี้"}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closeModal}
                  aria-label="ปิดหน้าต่าง"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 text-sm font-semibold text-slate-500 transition hover:border-slate-300 hover:bg-slate-100 hover:text-slate-700"
                >
                  X
                </button>
              </div>

              {formSubmitError && (
                <div
                  id={CLIENT_FORM_ALERT_ID}
                  tabIndex={-1}
                  className="mx-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
                >
                  {formSubmitError}
                </div>
              )}

              <div className="space-y-8 px-6">
                <section className="space-y-5">
                  <div className="space-y-2">
                    <label
                      className="block text-sm font-semibold text-slate-800"
                      htmlFor="client-name-input"
                    >
                      ชื่อ Project
                    </label>
                    <input
                      id="client-name-input"
                      type="text"
                      value={clientForm.client_name}
                      placeholder="เช่น ThaiPHC Dashboard"
                      onChange={(event) =>
                        setClientForm((prev) => ({
                          ...prev,
                          client_name: event.target.value,
                        }))
                      }
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                    />
                    {formErrors.client_name && (
                      <p className="text-xs text-rose-600">
                        {formErrors.client_name}
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <label
                      className="block text-sm font-semibold text-slate-800"
                      htmlFor="client-description-input"
                    >
                      คำอธิบาย (ถ้ามี)
                    </label>
                    <textarea
                      id="client-description-input"
                      rows={3}
                      value={clientForm.client_description}
                      placeholder="เช่น ส่วนควบคุมสำหรับทีมกรมควบคุมโรค"
                      onChange={(event) =>
                        setClientForm((prev) => ({
                          ...prev,
                          client_description: event.target.value,
                        }))
                      }
                      className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                    />
                  </div>
                  <div className="grid gap-5 md:grid-cols-2">
                    <div className="space-y-2">
                      <label
                        className="block text-sm font-semibold text-slate-800"
                        htmlFor="redirect-uri-input"
                      >
                        Redirect URI
                      </label>
                      <input
                        id="redirect-uri-input"
                        type="url"
                        value={clientForm.redirect_uri}
                        onChange={(event) =>
                          setClientForm((prev) => ({
                            ...prev,
                            redirect_uri: event.target.value,
                          }))
                        }
                        placeholder="https://example.com/oauth/callback"
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                      />
                      {formErrors.redirect_uri && (
                        <p className="text-xs text-rose-600">
                          {formErrors.redirect_uri}
                        </p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <label
                        className="block text-sm font-semibold text-slate-800"
                        htmlFor="login-url-input"
                      >
                        Login URL
                      </label>
                      <input
                        id="login-url-input"
                        type="url"
                        value={clientForm.login_url}
                        onChange={(event) =>
                          setClientForm((prev) => ({
                            ...prev,
                            login_url: event.target.value,
                          }))
                        }
                        placeholder="https://example.com/login"
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                      />
                      {formErrors.login_url && (
                        <p className="text-xs text-rose-600">
                          {formErrors.login_url}
                        </p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <label
                        className="block text-sm font-semibold text-slate-800"
                        htmlFor="consent-url-input"
                      >
                        Consent URL
                      </label>
                      <input
                        id="consent-url-input"
                        type="url"
                        value={clientForm.consent_url}
                        onChange={(event) =>
                          setClientForm((prev) => ({
                            ...prev,
                            consent_url: event.target.value,
                          }))
                        }
                        placeholder="https://example.com/consent"
                        className="w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm text-slate-800 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                      />
                      {formErrors.consent_url && (
                        <p className="text-xs text-rose-600">
                          {formErrors.consent_url}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <span className="block text-sm font-semibold text-slate-800">
                      Scope ที่อนุญาต
                    </span>
                    <p className="text-xs text-slate-500">
                      แบ่งเป็นหมวดหมู่เพื่อช่วยให้เลือกเฉพาะข้อมูลที่ต้องใช้จริง
                    </p>
                    <div
                      id="scopes-section"
                      tabIndex={-1}
                      className="space-y-4"
                    >
                      {SCOPE_GROUPS.map((group) => (
                        <div
                          key={group.title}
                          className="rounded-xl border border-slate-200 bg-white/60 p-4 shadow-sm"
                        >
                          <div className="mb-3">
                            <p className="text-sm font-semibold text-slate-800">
                              {group.title}
                            </p>
                            {group.helper ? (
                              <p className="mt-0.5 text-xs text-slate-500">
                                {group.helper}
                              </p>
                            ) : null}
                          </div>
                          <div className="grid gap-3 md:grid-cols-2">
                            {group.options.map((option) => {
                              const checked = clientForm.scopes.includes(
                                option.value
                              );
                              return (
                                <label
                                  key={option.value}
                                  className="flex items-start gap-3 rounded-lg border border-transparent bg-white px-3 py-2 text-sm text-slate-700 shadow-sm transition hover:border-emerald-200"
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => toggleScope(option.value)}
                                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                                  />
                                  <span>
                                    <span className="font-medium text-slate-800">
                                      {option.label}
                                    </span>
                                    {option.description ? (
                                      <span className="mt-0.5 block text-xs text-slate-500">
                                        {option.description}
                                      </span>
                                    ) : null}
                                  </span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                    {formErrors.scopes && (
                      <p className="text-xs text-rose-600">
                        {formErrors.scopes}
                      </p>
                    )}
                  </div>
                </section>

                <section className="space-y-5">
                  <div className="space-y-3">
                    <span className="block text-sm font-semibold text-slate-800">
                      ประเภท Grant ที่เปิดใช้
                    </span>
                    <div
                      id="grant-types-section"
                      tabIndex={-1}
                      className="space-y-4"
                    >
                      {GRANT_TYPE_GROUPS.map((group) => (
                        <div
                          key={group.title}
                          className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                        >
                          <div className="mb-2">
                            <p className="text-sm font-semibold text-slate-800">
                              {group.title}
                            </p>
                            {group.helper ? (
                              <p className="mt-0.5 text-xs text-slate-500">
                                {group.helper}
                              </p>
                            ) : null}
                          </div>
                          <div className="space-y-2">
                            {group.options.map((option) => {
                              const checked = clientForm.grant_types.includes(
                                option.value
                              );
                              return (
                                <label
                                  key={option.value}
                                  className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm"
                                >
                                  <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() =>
                                      toggleGrantType(option.value)
                                    }
                                    className="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                                  />
                                  <span>
                                    <span className="font-medium text-slate-800">
                                      {option.label}
                                    </span>
                                    {option.helper ? (
                                      <span className="block text-xs text-slate-500">
                                        {option.helper}
                                      </span>
                                    ) : null}
                                  </span>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                    {formErrors.grant_types && (
                      <p className="text-xs text-rose-600">
                        {formErrors.grant_types}
                      </p>
                    )}
                  </div>
                  <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
                    <label className="inline-flex items-start gap-3 text-sm font-medium text-emerald-800">
                      <input
                        type="checkbox"
                        checked={clientForm.public_client}
                        onChange={(event) =>
                          setClientForm((prev) => ({
                            ...prev,
                            public_client: event.target.checked,
                          }))
                        }
                        className="mt-0.5 h-4 w-4 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span>
                        Public client (ไม่มี client secret ตอนรันจริง)
                        <span className="mt-1 block text-xs font-normal text-emerald-700">
                          เหมาะสำหรับแอปมือถือหรือ web SPA ที่ไม่สามารถเก็บ
                          client secret ได้อย่างปลอดภัย
                        </span>
                      </span>
                    </label>
                  </div>
                </section>
              </div>

              <div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-5">
                <button
                  type="button"
                  onClick={closeModal}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
                  disabled={isSubmittingClient}
                >
                  ยกเลิก
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
                  disabled={isSubmittingClient}
                >
                  {isSubmittingClient
                    ? "กำลังบันทึก…"
                    : modalMode === "create"
                    ? "สร้าง Project"
                    : "บันทึกการเปลี่ยนแปลง"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClientAccessPage;
