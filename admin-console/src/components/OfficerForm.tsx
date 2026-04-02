import React, {
  ChangeEvent,
  forwardRef,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import DatePicker, {
  registerLocale,
  ReactDatePickerCustomHeaderProps,
} from "react-datepicker";
import Select, { StylesConfig } from "react-select";
import { th } from "date-fns/locale";
import {
  AdministrativeLevel,
  OfficerCreatePayload,
  OfficerDetail,
  OfficerUpdatePayload,
} from "../types/officer";
import { UserProfile } from "../types/auth";
import { fetchGenderItems, MetaItem } from "../api/meta";
import {
  fetchDistricts,
  fetchHealthAreas,
  fetchHealthServices,
  fetchPositions,
  fetchPrefixes,
  fetchSubdistricts,
  LookupItem,
} from "../api/lookups";
import { useAuthContext } from "../context/AuthContext";
import { useProvincesLookup } from "../hooks/useProvincesLookup";
import PasswordInput from "./PasswordInput";

registerLocale("th", th);

type OfficerFormMode = "create" | "edit";

type CreateFormValues = OfficerCreatePayload;
type EditFormValues = OfficerUpdatePayload;
type OfficerFormSubmitValues = OfficerCreatePayload | OfficerUpdatePayload;

type CombinedFormValues = Partial<CreateFormValues & EditFormValues>;
type GenderOption = { value: string; label: string };
type SelectOption = { value: string; label: string };

const THAI_YEAR_OFFSET = 543;
const thaiMonths = [
  "มกราคม",
  "กุมภาพันธ์",
  "มีนาคม",
  "เมษายน",
  "พฤษภาคม",
  "มิถุนายน",
  "กรกฎาคม",
  "สิงหาคม",
  "กันยายน",
  "ตุลาคม",
  "พฤศจิกายน",
  "ธันวาคม",
];

const pad = (value: number) => value.toString().padStart(2, "0");

const isoToDate = (value?: string): Date | null => {
  if (!value) {
    return null;
  }
  const parts = value.split("-");
  if (parts.length !== 3) {
    return null;
  }
  const [yearRaw, monthRaw, dayRaw] = parts.map((part) => parseInt(part, 10));
  if ([yearRaw, monthRaw, dayRaw].some((num) => Number.isNaN(num))) {
    return null;
  }
  const date = new Date(yearRaw, monthRaw - 1, dayRaw);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
};

const dateToIso = (date: Date | null): string | undefined => {
  if (!date) {
    return undefined;
  }
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${pad(year)}-${pad(month)}-${pad(day)}`;
};

const convertPickerValueToThai = (value?: string): string => {
  if (!value) {
    return "";
  }
  const parts = value.split("/");
  if (parts.length !== 3) {
    return value;
  }
  const [day, month, year] = parts;
  const numericYear = Number(year);
  if (Number.isNaN(numericYear)) {
    return value;
  }
  return `${day}/${month}/${numericYear + THAI_YEAR_OFFSET}`;
};

const SCOPE_PRIORITY: Record<AdministrativeLevel, number> = {
  village: 0,
  subdistrict: 1,
  district: 2,
  province: 3,
  area: 4,
  region: 5,
  country: 6,
};

const SCOPE_LABELS: Record<AdministrativeLevel, string> = {
  village: "ระดับหมู่บ้าน",
  subdistrict: "ระดับตำบล",
  district: "ระดับอำเภอ",
  province: "ระดับจังหวัด",
  area: "ระดับเขตสุขภาพ",
  region: "ระดับภาค",
  country: "ระดับประเทศ",
};

const normalizeScopeLevel = (
  value?: string | null,
): AdministrativeLevel | null => {
  if (!value) {
    return null;
  }
  const normalized = value.toLowerCase();
  if (Object.prototype.hasOwnProperty.call(SCOPE_PRIORITY, normalized)) {
    return normalized as AdministrativeLevel;
  }
  return null;
};

const buildFallbackLookupItem = (
  id?: string | null,
  name?: string | null,
  extra?: Partial<LookupItem>,
): LookupItem | null => {
  if (!id) {
    return null;
  }
  const label = name ?? id;
  return {
    id,
    label,
    name_th: name ?? undefined,
    code: id,
    scope_level: null,
    postal_code: null,
    province_code: undefined,
    district_code: undefined,
    subdistrict_code: undefined,
    region_code: undefined,
    region_name_th: undefined,
    region_name_en: undefined,
    ...extra,
  };
};

const resolveLookupValue = (item: LookupItem) => item.code ?? item.id;

const renderLookupLabel = (item: LookupItem) => {
  const code = resolveLookupValue(item);
  const baseLabel = item.name_th ?? item.label ?? item.name_en ?? code;
  if (!baseLabel) {
    return code;
  }
  if (!code || code === baseLabel) {
    return baseLabel;
  }
  return `${baseLabel} (${code})`;
};

const createLookupOptions = (items: LookupItem[]): SelectOption[] =>
  items
    .map((item) => {
      const value = resolveLookupValue(item) ?? "";
      const label = renderLookupLabel(item) ?? value;
      return { value, label };
    })
    .filter((option) => option.value);

const createPositionOptions = (items: LookupItem[]): SelectOption[] =>
  items
    .map((item) => {
      const value = item.id ?? "";
      const label = item.name_th ?? item.label ?? value;
      return { value, label };
    })
    .filter((option) => option.value);

const createPrefixOptions = (items: LookupItem[]): SelectOption[] =>
  items
    .map((item) => {
      const value = resolveLookupValue(item) ?? "";
      const label = item.name_th ?? item.label ?? value;
      return { value, label };
    })
    .filter((option) => option.value);

const normalizeHealthAreaCode = (value?: string | null): string => {
  const raw = (value ?? "").trim().toUpperCase();
  if (!raw) {
    return "";
  }
  if (raw.startsWith("HA")) {
    return raw.slice(2);
  }
  return raw;
};

const isSameHealthAreaCode = (
  left?: string | null,
  right?: string | null,
): boolean => {
  const normalizedLeft = normalizeHealthAreaCode(left);
  const normalizedRight = normalizeHealthAreaCode(right);
  if (!normalizedLeft || !normalizedRight) {
    return false;
  }
  return normalizedLeft === normalizedRight;
};

const findOption = (
  options: SelectOption[],
  value?: string | null,
): SelectOption | null =>
  options.find((option) => option.value === value) ?? null;

const selectStyles: StylesConfig<SelectOption, false> = {
  control: (base, state) => ({
    ...base,
    minHeight: "2.75rem",
    borderRadius: "0.75rem",
    borderColor: state.isFocused ? "#3b82f6" : "#e2e8f0",
    boxShadow: state.isFocused ? "0 0 0 2px rgba(59, 130, 246, 0.2)" : "none",
    backgroundColor: state.isDisabled ? "#f8fafc" : "#ffffff",
    "&:hover": {
      borderColor: "#3b82f6",
    },
  }),
  valueContainer: (base) => ({
    ...base,
    padding: "0 0.75rem",
  }),
  input: (base) => ({
    ...base,
    margin: 0,
    padding: 0,
  }),
  placeholder: (base) => ({
    ...base,
    color: "#94a3b8",
  }),
  singleValue: (base) => ({
    ...base,
    color: "#1e293b",
  }),
  indicatorsContainer: (base) => ({
    ...base,
    height: "2.75rem",
  }),
  menu: (base) => ({
    ...base,
    zIndex: 50,
  }),
  option: (base, state) => ({
    ...base,
    backgroundColor: state.isSelected
      ? "#bae6fd"
      : state.isFocused
        ? "#e0f2fe"
        : "#ffffff",
    color: "#0f172a",
    fontSize: "0.875rem",
  }),
};

const normalizeOptionalText = (value?: string | null): string | null => {
  if (typeof value !== "string") {
    return value ?? null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
};

const ensureLookupIncludes = (
  items: LookupItem[],
  targetId?: string | null,
  targetName?: string | null,
): LookupItem[] => {
  if (!targetId) {
    return items;
  }
  const alreadyExists = items.some((item) => {
    const value = resolveLookupValue(item);
    return value === targetId || item.id === targetId;
  });
  if (alreadyExists) {
    return items;
  }
  const fallback = buildFallbackLookupItem(targetId, targetName);
  if (!fallback) {
    return items;
  }
  return [fallback, ...items];
};

const deriveUserScopeLevel = (
  profile: UserProfile | null,
): AdministrativeLevel | null => {
  if (!profile) {
    return null;
  }
  const positionScope = normalizeScopeLevel(
    profile.position_scope_level ?? null,
  );
  if (positionScope) {
    return positionScope;
  }
  const hasGranularLocation = Boolean(
    profile.subdistrict_code ||
    profile.district_code ||
    profile.province_code ||
    profile.health_area_code ||
    profile.area_code,
  );
  // Admin accounts without any granular location codes are treated as department-level (country scope).
  if (profile.is_admin && !hasGranularLocation) {
    return "country";
  }
  if (profile.subdistrict_code) {
    return "subdistrict";
  }
  if (profile.district_code) {
    return "district";
  }
  if (profile.province_code) {
    return "province";
  }
  if (profile.health_area_code || profile.area_code) {
    return "area";
  }
  if (profile.region_code) {
    return "region";
  }
  return "country";
};

type ThaiDateInputProps = {
  value?: string;
  onClick?: () => void;
  placeholder: string;
  disabled?: boolean;
};

const ThaiDateInput = forwardRef<HTMLButtonElement, ThaiDateInputProps>(
  ({ value, onClick, placeholder, disabled }, ref) => {
    const displayValue = value ? convertPickerValueToThai(value) : "";
    const showPlaceholder = !displayValue;
    return (
      <button
        type="button"
        onClick={onClick}
        ref={ref}
        disabled={disabled}
        className="datepicker-trigger"
      >
        <span className={showPlaceholder ? "placeholder" : undefined}>
          {displayValue || placeholder}
        </span>
        <svg
          className="h-4 w-4 text-slate-400"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M7 4V6M17 4V6M4 9H20M6 12H6.01M10 12H14M18 12H18.01M6 16H6.01M10 16H14M18 16H18.01M5 5H19C20.1046 5 21 5.89543 21 7V19C21 20.1046 20.1046 21 19 21H5C3.89543 21 3 20.1046 3 19V7C3 5.89543 3.89543 5 5 5Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    );
  },
);
ThaiDateInput.displayName = "ThaiDateInput";

interface ThaiHeaderProps extends ReactDatePickerCustomHeaderProps {
  availableYears: number[];
}

const renderThaiHeader = ({
  date,
  decreaseMonth,
  increaseMonth,
  changeYear,
  changeMonth,
  prevMonthButtonDisabled,
  nextMonthButtonDisabled,
  availableYears,
}: ThaiHeaderProps) => {
  const currentMonth = date.getMonth();
  const currentYear = date.getFullYear();

  return (
    <div className="flex items-center justify-between gap-2 px-2 py-1">
      <button
        type="button"
        onClick={decreaseMonth}
        disabled={prevMonthButtonDisabled}
        className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <span className="sr-only">เดือนก่อนหน้า</span>
        <svg
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M12.5 15L7.5 10L12.5 5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      <div className="flex items-center gap-2">
        <select
          className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-200"
          value={currentMonth}
          onChange={(event) => changeMonth(Number(event.target.value))}
        >
          {thaiMonths.map((label, index) => (
            <option key={label} value={index}>
              {label}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-200"
          value={currentYear}
          onChange={(event) => changeYear(Number(event.target.value))}
        >
          {availableYears.map((year) => (
            <option key={year} value={year}>
              {year + THAI_YEAR_OFFSET}
            </option>
          ))}
        </select>
      </div>
      <button
        type="button"
        onClick={increaseMonth}
        disabled={nextMonthButtonDisabled}
        className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <span className="sr-only">เดือนถัดไป</span>
        <svg
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M7.5 5L12.5 10L7.5 15"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </div>
  );
};

const sanitizeInitialValues = (
  values?: Partial<OfficerDetail>,
): CombinedFormValues => {
  if (!values) {
    return {};
  }

  const cleaned: CombinedFormValues = {};
  Object.entries(values).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      return;
    }
    if (key === "area_type" && typeof value === "string") {
      cleaned.area_type = value as AdministrativeLevel;
      return;
    }
    if (key === "gender" && typeof value === "string") {
      cleaned.gender = value.toLowerCase();
      return;
    }
    (cleaned as Record<string, unknown>)[key] = value;
  });
  return cleaned;
};

interface OfficerFormProps {
  mode: OfficerFormMode;
  initialValues?: Partial<OfficerDetail>;
  onSubmit: (values: OfficerFormSubmitValues) => Promise<void> | void;
  isSubmitting?: boolean;
  submitLabel?: string;
}

const defaultCreateValues: CreateFormValues = {
  citizen_id: "",
  prefix_id: "",
  first_name: "",
  last_name: "",
  gender: "",
  birth_date: "",
  email: "",
  phone: "",
  position_id: "",
  address_number: "",
  province_id: "",
  district_id: "",
  subdistrict_id: "",
  village_no: "",
  alley: "",
  street: "",
  postal_code: "",
  health_area_id: "",
  health_service_id: "",
  area_type: undefined,
  area_code: "",
  password: "",
};

const UPDATE_ALLOWED_KEYS: Array<keyof OfficerUpdatePayload> = [
  "prefix_id",
  "first_name",
  "last_name",
  "gender",
  "birth_date",
  "email",
  "phone",
  "position_id",
  "address_number",
  "province_id",
  "district_id",
  "subdistrict_id",
  "village_no",
  "alley",
  "street",
  "postal_code",
  "health_area_id",
  "health_service_id",
  "area_type",
  "area_code",
];

const buildUpdatePayload = (
  values: CombinedFormValues,
): OfficerUpdatePayload => {
  const payload: Partial<OfficerUpdatePayload> = {};
  UPDATE_ALLOWED_KEYS.forEach((key) => {
    const value = values[key as keyof CombinedFormValues];
    if (value !== undefined) {
      (payload as Record<string, unknown>)[key] = value;
    }
  });
  return payload as OfficerUpdatePayload;
};

export const OfficerForm: React.FC<OfficerFormProps> = ({
  mode,
  initialValues,
  onSubmit,
  isSubmitting = false,
  submitLabel,
}) => {
  const positionFallback = useMemo(
    () =>
      buildFallbackLookupItem(
        initialValues?.position_id ?? null,
        initialValues?.position_name_th ?? null,
        { scope_level: initialValues?.area_type ?? null },
      ),
    [
      initialValues?.position_id,
      initialValues?.position_name_th,
      initialValues?.area_type,
    ],
  );
  const districtFallback = useMemo(
    () =>
      buildFallbackLookupItem(
        initialValues?.district_id ?? null,
        initialValues?.district_name_th ?? null,
      ),
    [initialValues?.district_id, initialValues?.district_name_th],
  );
  const subdistrictFallback = useMemo(
    () =>
      buildFallbackLookupItem(
        initialValues?.subdistrict_id ?? null,
        initialValues?.subdistrict_name_th ?? null,
      ),
    [initialValues?.subdistrict_id, initialValues?.subdistrict_name_th],
  );
  const healthServiceFallback = useMemo(
    () =>
      buildFallbackLookupItem(
        initialValues?.health_service_id ?? null,
        initialValues?.health_service_name_th ?? null,
      ),
    [initialValues?.health_service_id, initialValues?.health_service_name_th],
  );
  const { user } = useAuthContext();
  const permissionScope = user?.permission_scope ?? null;
  const scopeCodes = permissionScope?.codes ?? {};
  const explicitPermissionScopeLevel =
    normalizeScopeLevel(permissionScope?.level ?? null);
  const fallbackHealthAreaFromAreaCode =
    explicitPermissionScopeLevel === "area"
      ? normalizeOptionalText(user?.area_code ?? null)
      : null;
  const enforcedHealthAreaId =
    normalizeOptionalText(scopeCodes.health_area_id ?? null) ??
    normalizeOptionalText(user?.health_area_code ?? null) ??
    fallbackHealthAreaFromAreaCode;
  const enforcedHealthAreaName = normalizeOptionalText(user?.health_area_name ?? null);
  const enforcedProvinceId =
    scopeCodes.province_id ?? user?.province_code ?? null;
  const enforcedProvinceName =
    scopeCodes.province_name_th ?? user?.province_name ?? null;
  const enforcedDistrictId =
    scopeCodes.district_id ?? user?.district_code ?? null;
  const enforcedDistrictName =
    scopeCodes.district_name_th ?? user?.district_name ?? null;
  const enforcedSubdistrictId =
    scopeCodes.subdistrict_id ?? user?.subdistrict_code ?? null;
  const enforcedSubdistrictName =
    scopeCodes.subdistrict_name_th ?? user?.subdistrict_name ?? null;
  const enforcedHealthServiceId =
    normalizeOptionalText(scopeCodes.health_service_id ?? null) ??
    normalizeOptionalText(user?.health_service_id ?? null);
  const enforcedHealthServiceName =
    normalizeOptionalText(scopeCodes.health_service_name_th ?? null) ??
    normalizeOptionalText(user?.health_service_name_th ?? null);
  const enforcedVillageCode =
    scopeCodes.village_code ?? user?.area_code ?? null;
  const enforcedVillageName =
    scopeCodes.village_name_th ?? user?.area_name ?? null;
  const permissionScopeLevel = explicitPermissionScopeLevel;
  const initialProvinceId = initialValues?.province_id ?? null;
  const initialProvinceName = initialValues?.province_name_th ?? null;
  const [formValues, setFormValues] = useState<CombinedFormValues>(() => {
    const sanitized = sanitizeInitialValues(initialValues);
    if (mode === "create") {
      const enforcedDefaults: CombinedFormValues = {};
      if (enforcedProvinceId) {
        enforcedDefaults.province_id = enforcedProvinceId;
      }
      if (enforcedDistrictId) {
        enforcedDefaults.district_id = enforcedDistrictId;
      }
      if (enforcedSubdistrictId) {
        enforcedDefaults.subdistrict_id = enforcedSubdistrictId;
      }
      if (enforcedHealthAreaId) {
        enforcedDefaults.health_area_id = enforcedHealthAreaId;
      }
      if (enforcedHealthServiceId) {
        enforcedDefaults.health_service_id = enforcedHealthServiceId;
      }
      if (enforcedVillageCode) {
        enforcedDefaults.area_code = enforcedVillageCode;
      }
      return { ...defaultCreateValues, ...enforcedDefaults, ...sanitized };
    }
    return sanitized;
  });
  const [selectedBirthDate, setSelectedBirthDate] = useState<Date | null>(() =>
    isoToDate(initialValues?.birth_date as string | undefined),
  );
  const [birthDateError, setBirthDateError] = useState<string | null>(null);
  const [healthServiceError, setHealthServiceError] = useState<string | null>(
    null,
  );
  const [positionError, setPositionError] = useState<string | null>(null);

  const initialPositionFallback = buildFallbackLookupItem(
    initialValues?.position_id ?? null,
    initialValues?.position_name_th ?? null,
    { scope_level: initialValues?.area_type ?? null },
  );
  const [prefixes, setPrefixes] = useState<LookupItem[]>([]);
  const [positions, setPositions] = useState<LookupItem[]>([]);
  const [genders, setGenders] = useState<MetaItem[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const {
    provinces: provinceOptionsRaw,
    loading: loadingProvinces,
    error: provincesError,
  } = useProvincesLookup();
  const [districts, setDistricts] = useState<LookupItem[]>([]);
  const [subdistricts, setSubdistricts] = useState<LookupItem[]>([]);
  const [healthAreas, setHealthAreas] = useState<LookupItem[]>([]);
  const [healthServices, setHealthServices] = useState<LookupItem[]>([]);
  const [isLoadingDistricts, setIsLoadingDistricts] = useState(false);
  const [isLoadingSubdistricts, setIsLoadingSubdistricts] = useState(false);
  const [isLoadingHealthServices, setIsLoadingHealthServices] = useState(false);

  useEffect(() => {
    if (mode !== "create") {
      return;
    }
    setFormValues((prev: CombinedFormValues) => {
      const next = { ...prev };
      let changed = false;
      if (enforcedProvinceId && next.province_id !== enforcedProvinceId) {
        next.province_id = enforcedProvinceId;
        changed = true;
      }
      if (enforcedDistrictId && next.district_id !== enforcedDistrictId) {
        next.district_id = enforcedDistrictId;
        changed = true;
      }
      if (
        enforcedSubdistrictId &&
        next.subdistrict_id !== enforcedSubdistrictId
      ) {
        next.subdistrict_id = enforcedSubdistrictId;
        changed = true;
      }
      if (
        enforcedHealthAreaId &&
        next.health_area_id !== enforcedHealthAreaId
      ) {
        next.health_area_id = enforcedHealthAreaId;
        changed = true;
      }
      if (
        enforcedHealthServiceId &&
        next.health_service_id !== enforcedHealthServiceId
      ) {
        next.health_service_id = enforcedHealthServiceId;
        changed = true;
      }
      if (enforcedVillageCode && next.area_code !== enforcedVillageCode) {
        next.area_code = enforcedVillageCode;
        changed = true;
      }
      if (!changed) {
        return prev;
      }
      return next;
    });
  }, [
    mode,
    enforcedProvinceId,
    enforcedDistrictId,
    enforcedSubdistrictId,
    enforcedHealthAreaId,
    enforcedHealthServiceId,
    enforcedVillageCode,
  ]);

  useEffect(() => {
    if (!positionFallback) {
      return;
    }
    if (positions.some((item) => item.id === positionFallback.id)) {
      return;
    }
    setPositions((prev) => [...prev, positionFallback]);
  }, [positionFallback, positions]);

  useEffect(() => {
    if (!districtFallback) {
      return;
    }
    if (districts.some((item) => item.id === districtFallback.id)) {
      return;
    }
    setDistricts((prev) => [...prev, districtFallback]);
  }, [districtFallback, districts]);

  useEffect(() => {
    if (!subdistrictFallback) {
      return;
    }
    if (subdistricts.some((item) => item.id === subdistrictFallback.id)) {
      return;
    }
    setSubdistricts((prev) => [...prev, subdistrictFallback]);
  }, [subdistrictFallback, subdistricts]);

  useEffect(() => {
    if (!healthServiceFallback) {
      return;
    }
    if (healthServices.some((item) => item.id === healthServiceFallback.id)) {
      return;
    }
    setHealthServices((prev) => [...prev, healthServiceFallback]);
  }, [healthServiceFallback, healthServices]);
  const userScopeLevel = useMemo(() => deriveUserScopeLevel(user), [user]);
  const filteredPositions = useMemo(() => {
    if (!positions.length || !userScopeLevel) {
      return positions
        .filter((item) => {
          const code = (item.code ?? "").toUpperCase();
          return !["DIR", "VIL"].includes(code);
        })
        .sort((a, b) => {
          const scopeA = normalizeScopeLevel(a.scope_level ?? null);
          const scopeB = normalizeScopeLevel(b.scope_level ?? null);
          const rankA = scopeA ? SCOPE_PRIORITY[scopeA] : -1;
          const rankB = scopeB ? SCOPE_PRIORITY[scopeB] : -1;
          if (rankA !== rankB) {
            return rankB - rankA;
          }
          return (a.name_th ?? a.label ?? "").localeCompare(
            b.name_th ?? b.label ?? "",
          );
        });
    }
    const userRank = SCOPE_PRIORITY[userScopeLevel];
    const currentPositionId = (formValues.position_id as string) ?? null;
    return positions
      .filter((item) => {
        const code = (item.code ?? "").toUpperCase();
        if (["DIR", "VIL"].includes(code)) {
          return false;
        }
        if (currentPositionId && item.id === currentPositionId) {
          return true;
        }
        const scope = normalizeScopeLevel(item.scope_level ?? null);
        if (!scope) {
          return true;
        }
        return SCOPE_PRIORITY[scope] <= userRank;
      })
      .sort((a, b) => {
        const scopeA = normalizeScopeLevel(a.scope_level ?? null);
        const scopeB = normalizeScopeLevel(b.scope_level ?? null);
        const rankA = scopeA ? SCOPE_PRIORITY[scopeA] : -1;
        const rankB = scopeB ? SCOPE_PRIORITY[scopeB] : -1;
        if (rankA !== rankB) {
          return rankB - rankA;
        }
        return (a.name_th ?? a.label ?? "").localeCompare(
          b.name_th ?? b.label ?? "",
        );
      });
  }, [positions, userScopeLevel, formValues.position_id]);
  const hasPositionRestriction =
    Boolean(userScopeLevel) && filteredPositions.length < positions.length;
  const isPositionSelectionDisabled = filteredPositions.length === 0;
  const userScopeLabel = userScopeLevel ? SCOPE_LABELS[userScopeLevel] : null;
  const enforcedHealthAreaLabel = useMemo(() => {
    if (!enforcedHealthAreaId) {
      return null;
    }
    const found = healthAreas.find(
      (item) => resolveLookupValue(item) === enforcedHealthAreaId,
    );
    if (found) {
      return renderLookupLabel(found);
    }
    return enforcedHealthAreaId;
  }, [enforcedHealthAreaId, healthAreas]);

  const hasLoadedInitialLookupsRef = useRef(false);
  const lastDistrictFetchKey = useRef<string | null>(null);
  const lastSubdistrictFetchKey = useRef<string | null>(null);

  useEffect(() => {
    if (hasLoadedInitialLookupsRef.current) {
      return;
    }
    hasLoadedInitialLookupsRef.current = true;
    const loadMeta = async () => {
      try {
        const [prefixItems, positionItems, genderItems, healthAreaItems] =
          await Promise.all([
            fetchPrefixes(),
            fetchPositions(),
            fetchGenderItems(),
            fetchHealthAreas(),
          ]);
        setPrefixes(prefixItems);
        setPositions(positionItems);
        setGenders(genderItems);
        setHealthAreas(healthAreaItems);
      } catch (error) {
        // Non-blocking; user can still provide raw identifiers.
      } finally {
        setLoadingMeta(false);
      }
    };

    loadMeta();
  }, []);

  useEffect(() => {
    if (!initialValues) {
      return;
    }
    const sanitized = sanitizeInitialValues(initialValues);
    setFormValues((prev: CombinedFormValues) => ({ ...prev, ...sanitized }));
    if (sanitized.birth_date) {
      setSelectedBirthDate(isoToDate(sanitized.birth_date as string));
    }
  }, [initialValues]);

  useEffect(() => {
    const isoValue = formValues.birth_date as string | undefined;
    setSelectedBirthDate(isoToDate(isoValue));
    if (isoValue) {
      setBirthDateError(null);
    }
  }, [formValues.birth_date]);

  const handleChange =
    (field: keyof CombinedFormValues) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = event.target.value;
      setFormValues((prev: CombinedFormValues) => ({
        ...prev,
        [field]: value === "" ? undefined : value,
      }));
      if (field === "health_service_id") {
        setHealthServiceError(null);
      }
    };

  const generateSimplePassword = (length = 8) => {
    const digits = "0123456789";
    let result = "";
    for (let i = 0; i < length; i += 1) {
      result += digits[Math.floor(Math.random() * digits.length)];
    }
    return result;
  };

  const handleGeneratePassword = () => {
    const generated = generateSimplePassword(8);
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      password: generated,
    }));
  };

  useEffect(() => {
    if (!formValues.position_id) {
      return;
    }
    if (!positions.length) {
      return;
    }
    if (!filteredPositions.some((item) => item.id === formValues.position_id)) {
      setFormValues((prev: CombinedFormValues) => ({
        ...prev,
        position_id: undefined,
      }));
    }
  }, [filteredPositions, formValues.position_id, positions.length]);

  useEffect(() => {
    const positionId = (formValues.position_id as string) ?? "";
    if (!positionId) {
      return;
    }
    const selectedPosition = positions.find((item) => item.id === positionId);
    if (!selectedPosition) {
      return;
    }
    const scope = normalizeScopeLevel(selectedPosition.scope_level ?? null);
    if (!scope) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => {
      const current = prev.area_type as AdministrativeLevel | undefined;
      if (current === scope) {
        return prev;
      }
      return { ...prev, area_type: scope };
    });
  }, [formValues.position_id, positions]);

  const applyPositionScope = <
    T extends {
      position_id?: string;
      area_type?: AdministrativeLevel | undefined;
    },
  >(
    values: T,
  ): T => {
    const positionId = values.position_id;
    if (!positionId) {
      return values;
    }
    const found = positions.find((item) => item.id === positionId);
    const scope = normalizeScopeLevel(found?.scope_level ?? null);
    if (!scope) {
      return { ...values, area_type: values.area_type };
    }
    if (values.area_type === scope) {
      return values;
    }
    return { ...values, area_type: scope };
  };

  const normalizeOfficerPayload = <T extends { gender?: string | undefined }>(
    values: T,
  ): T => {
    const genderRaw = values.gender;
    if (!genderRaw) {
      return values;
    }
    const normalized = genderRaw.trim().toLowerCase();
    const genderMap: Record<string, string> = {
      male: "male",
      m: "male",
      female: "female",
      f: "female",
      woman: "female",
      girl: "female",
      lady: "female",
      other: "other",
    };
    const resolved = genderMap[normalized] ?? normalized;
    if (resolved === genderRaw) {
      return values;
    }
    return { ...values, gender: resolved };
  };

  const sanitizeCreatePayload = (
    values: OfficerCreatePayload,
  ): OfficerCreatePayload => {
    const next: OfficerCreatePayload = { ...values };
    const optionalStringKeys: Array<keyof OfficerCreatePayload> = [
      "gender",
      "birth_date",
      "email",
      "phone",
      "profile_image",
      "province_id",
      "district_id",
      "subdistrict_id",
      "village_no",
      "alley",
      "street",
      "postal_code",
      "municipality_id",
      "health_area_id",
      "health_service_id",
      "area_code",
    ];

    optionalStringKeys.forEach((key) => {
      const value = next[key];
      if (typeof value !== "string") {
        return;
      }
      if (!value.trim()) {
        delete next[key];
      }
    });

    return next;
  };

  const handleProvinceChange = (value: string) => {
    if (shouldLockProvince) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      province_id: value === "" ? undefined : value,
      district_id: undefined,
      subdistrict_id: undefined,
      health_service_id: undefined,
    }));
    setDistricts([]);
    setSubdistricts([]);
    setHealthServices([]);
  };

  const handleDistrictChange = (value: string) => {
    if (shouldLockDistrict) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      district_id: value === "" ? undefined : value,
      subdistrict_id: undefined,
      health_service_id: undefined,
    }));
    setSubdistricts([]);
    setHealthServices([]);
  };

  const handleSubdistrictChange = (value: string) => {
    if (shouldLockSubdistrict) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      subdistrict_id: value === "" ? undefined : value,
      health_service_id: undefined,
    }));
    setHealthServices([]);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    
    if (formValues.birth_date) {
      const birthDate = isoToDate(formValues.birth_date as string | undefined);
      if (!birthDate) {
        setBirthDateError("กรุณาเลือกวันเดือนปีเกิดให้ถูกต้อง");
        return;
      }
      if (birthDate > minimumAdultBirthDate) {
        setBirthDateError("อายุยังไม่ครบ 18 ปีบริบูรณ์ ไม่สามารถสมัครได้");
        return;
      }
    }

    if (!formValues.position_id) {
      setPositionError("กรุณาเลือกตำแหน่งก่อนบันทึก");
      return;
    }
    if (requiresHealthService && !formValues.health_service_id) {
      setHealthServiceError("กรุณาเลือกหน่วยบริการสุขภาพ");
      return;
    }
    if (mode === "create") {
      const payload = sanitizeCreatePayload(
        normalizeOfficerPayload(
          applyPositionScope({
            ...defaultCreateValues,
            ...(formValues as CombinedFormValues),
          }),
        ) as OfficerCreatePayload,
      );
      await onSubmit(payload);
      return;
    }

    const { citizen_id, password, ...rest } = formValues;
    const aligned = normalizeOfficerPayload(
      applyPositionScope(rest as CombinedFormValues),
    );
    const payload = buildUpdatePayload(aligned as CombinedFormValues);
    await onSubmit(payload);
  };

  const genderOptions = useMemo<GenderOption[]>(() => {
    const fallbackLabels: Record<string, string> = {
      male: "ชาย",
      female: "หญิง",
      other: "อื่นๆ",
      m: "ชาย",
      f: "หญิง",
    };

    const normalized = genders
      .map((item: MetaItem) => {
        const rawValueRaw =
          typeof item.code === "string" && item.code.trim()
            ? item.code.trim()
            : typeof item.value === "string" && item.value.trim()
              ? item.value.trim()
              : typeof item.id !== "undefined"
                ? String(item.id)
                : "";

        const rawValue = rawValueRaw.toLowerCase();

        if (!rawValue) {
          return null;
        }

        const label =
          fallbackLabels[rawValue] ??
          item.name_th ??
          item.name_en ??
          rawValueRaw;
        return { value: rawValue, label };
      })
      .filter((option): option is GenderOption => Boolean(option));

    if (normalized.length > 0) {
      return normalized;
    }

    return [
      { value: "male", label: fallbackLabels.male },
      { value: "female", label: fallbackLabels.female },
      { value: "other", label: fallbackLabels.other },
    ];
  }, [genders]);

  const availableYears = useMemo(() => {
    const currentYear = new Date().getFullYear();
    const lowerBound = currentYear - 120;
    const years: number[] = [];
    for (let year = currentYear; year >= lowerBound; year -= 1) {
      years.push(year);
    }
    return years;
  }, []);

  const maxSelectableBirthYear = useMemo(
    () => new Date().getFullYear() - 17,
    [],
  );
  const maxSelectableBirthDate = useMemo(
    () => new Date(maxSelectableBirthYear, 11, 31),
    [maxSelectableBirthYear],
  );
  const minimumAdultBirthDate = useMemo(() => {
    const today = new Date();
    return new Date(
      today.getFullYear() - 18,
      today.getMonth(),
      today.getDate(),
    );
  }, []);

  const selectedPosition = useMemo(() => {
    const positionId = (formValues.position_id as string) ?? "";
    return positions.find((item) => item.id === positionId);
  }, [formValues.position_id, positions]);
  const lockedAreaScope = normalizeScopeLevel(
    selectedPosition?.scope_level ?? null,
  );
  const requiresProvince = Boolean(
    lockedAreaScope &&
    ["province", "district", "subdistrict", "village"].includes(
      lockedAreaScope,
    ),
  );
  const requiresDistrict = Boolean(
    lockedAreaScope &&
    ["district", "subdistrict", "village"].includes(lockedAreaScope),
  );
  const requiresSubdistrict = Boolean(
    lockedAreaScope && ["subdistrict", "village"].includes(lockedAreaScope),
  );
  const requiresHealthArea = lockedAreaScope === "area";
  const requiresHealthService = lockedAreaScope === "subdistrict";
  const requiresVillageCode = lockedAreaScope === "village";
  const shouldLockProvince =
    mode === "create" &&
    Boolean(enforcedProvinceId) &&
    permissionScopeLevel !== null &&
    SCOPE_PRIORITY[permissionScopeLevel] <= SCOPE_PRIORITY.province;
  const shouldLockDistrict =
    mode === "create" &&
    Boolean(enforcedDistrictId) &&
    permissionScopeLevel !== null &&
    SCOPE_PRIORITY[permissionScopeLevel] <= SCOPE_PRIORITY.district;
  const shouldLockSubdistrict =
    mode === "create" &&
    Boolean(enforcedSubdistrictId) &&
    permissionScopeLevel !== null &&
    SCOPE_PRIORITY[permissionScopeLevel] <= SCOPE_PRIORITY.subdistrict;
  const shouldLockHealthArea =
    mode === "create" &&
    Boolean(enforcedHealthAreaId) &&
    permissionScopeLevel !== null &&
    SCOPE_PRIORITY[permissionScopeLevel] <= SCOPE_PRIORITY.area;
  const shouldLockHealthService =
    mode === "create" &&
    Boolean(enforcedHealthServiceId) &&
    permissionScopeLevel === "subdistrict";
  const selectedProvince =
    (typeof formValues.province_id === "string" &&
    formValues.province_id.trim() !== ""
      ? formValues.province_id
      : shouldLockProvince
        ? enforcedProvinceId
        : "") ?? "";
  const selectedDistrict =
    (typeof formValues.district_id === "string" &&
    formValues.district_id.trim() !== ""
      ? formValues.district_id
      : shouldLockDistrict
        ? enforcedDistrictId
        : "") ?? "";
  const selectedSubdistrict =
    (typeof formValues.subdistrict_id === "string" &&
    formValues.subdistrict_id.trim() !== ""
      ? formValues.subdistrict_id
      : shouldLockSubdistrict
        ? enforcedSubdistrictId
        : "") ?? "";
  const scopedProvinceOptionsRaw = useMemo(() => {
    if (mode !== "create") {
      return provinceOptionsRaw;
    }

    const scopeLevel = permissionScope?.level ?? null;
    const scopeRegionCode = scopeCodes.region_code ?? user?.region_code ?? null;
    const scopeHealthAreaId =
      scopeCodes.health_area_id ?? user?.health_area_code ?? null;
    const scopeProvinceId = scopeCodes.province_id ?? user?.province_code ?? null;

    if (scopeLevel === "region" && scopeRegionCode) {
      return provinceOptionsRaw.filter(
        (item) => (item.region_code ?? null) === scopeRegionCode,
      );
    }

    if (scopeLevel === "area" && scopeHealthAreaId) {
      return provinceOptionsRaw.filter(
        (item) => (item.health_area_id ?? null) === scopeHealthAreaId,
      );
    }

    if (
      ["province", "district", "subdistrict", "village"].includes(
        scopeLevel ?? "",
      ) &&
      scopeProvinceId
    ) {
      return provinceOptionsRaw.filter(
        (item) => (resolveLookupValue(item) ?? "") === scopeProvinceId,
      );
    }

    return provinceOptionsRaw;
  }, [mode, provinceOptionsRaw, permissionScope?.level, scopeCodes, user]);
  const provinces = useMemo(() => {
    let items = scopedProvinceOptionsRaw;
    if (initialProvinceId) {
      items = ensureLookupIncludes(
        items,
        initialProvinceId,
        initialProvinceName,
      );
    }
    if (enforcedProvinceId) {
      items = ensureLookupIncludes(
        items,
        enforcedProvinceId,
        enforcedProvinceName,
      );
    }
    return items;
  }, [
    scopedProvinceOptionsRaw,
    initialProvinceId,
    initialProvinceName,
    enforcedProvinceId,
    enforcedProvinceName,
  ]);
  const prefixSelectOptions = useMemo(
    () => createPrefixOptions(prefixes),
    [prefixes],
  );
  const genderSelectOptions = useMemo<SelectOption[]>(
    () =>
      genderOptions.map((option) => ({
        value: option.value,
        label: option.label,
      })),
    [genderOptions],
  );
  const positionSelectOptions = useMemo(
    () => createPositionOptions(filteredPositions),
    [filteredPositions],
  );
  const provinceSelectOptions = useMemo(
    () => createLookupOptions(provinces),
    [provinces],
  );
  const districtSelectOptions = useMemo(
    () => createLookupOptions(districts),
    [districts],
  );
  const subdistrictSelectOptions = useMemo(
    () => createLookupOptions(subdistricts),
    [subdistricts],
  );
  const healthServiceSelectOptions = useMemo(
    () => createLookupOptions(healthServices),
    [healthServices],
  );
  const healthAreaLookupItems = useMemo(() => {
    let items = healthAreas;
    if (mode === "create" && permissionScopeLevel === "area" && enforcedHealthAreaId) {
      items = items.filter((item) => {
        const value = resolveLookupValue(item);
        return (
          isSameHealthAreaCode(value, enforcedHealthAreaId) ||
          isSameHealthAreaCode(item.id, enforcedHealthAreaId)
        );
      });
    }
    if (enforcedHealthAreaId) {
      items = ensureLookupIncludes(items, enforcedHealthAreaId, enforcedHealthAreaName);
    }
    return items;
  }, [
    healthAreas,
    mode,
    permissionScopeLevel,
    enforcedHealthAreaId,
    enforcedHealthAreaName,
  ]);
  const healthAreaSelectOptions = useMemo(
    () => createLookupOptions(healthAreaLookupItems),
    [healthAreaLookupItems],
  );
  const selectedHealthAreaValue = useMemo(() => {
    const currentValue =
      typeof formValues.health_area_id === "string"
        ? formValues.health_area_id
        : "";
    if (!currentValue) {
      return currentValue;
    }
    const exact = healthAreaSelectOptions.find(
      (option) => option.value === currentValue,
    );
    if (exact) {
      return exact.value;
    }
    const normalized = healthAreaSelectOptions.find((option) =>
      isSameHealthAreaCode(option.value, currentValue),
    );
    return normalized?.value ?? currentValue;
  }, [formValues.health_area_id, healthAreaSelectOptions]);
  const showProvinceLoading = loadingMeta || loadingProvinces;
  const showDistrictLoading = isLoadingDistricts && !shouldLockDistrict;
  const showSubdistrictLoading =
    isLoadingSubdistricts && !shouldLockSubdistrict;
  const showAreaScopeProvinceHint =
    mode === "create" && permissionScope?.level === "area" && Boolean(enforcedHealthAreaId);

  useEffect(() => {
    if (mode !== "create") {
      return;
    }
    if (!selectedProvince) {
      return;
    }
    const existsInScope = provinces.some(
      (item) => (resolveLookupValue(item) ?? "") === selectedProvince,
    );
    if (existsInScope) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      province_id: undefined,
      district_id: undefined,
      subdistrict_id: undefined,
      health_service_id: undefined,
    }));
    setDistricts([]);
    setSubdistricts([]);
    setHealthServices([]);
  }, [mode, provinces, selectedProvince]);

  useEffect(() => {
    if (!lockedAreaScope) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => {
      const next = { ...prev };
      let changed = false;

      if (!requiresProvince) {
        if (next.province_id) {
          next.province_id = undefined;
          changed = true;
        }
        if (next.district_id) {
          next.district_id = undefined;
          changed = true;
        }
        if (next.subdistrict_id) {
          next.subdistrict_id = undefined;
          changed = true;
        }
        if (next.health_service_id) {
          next.health_service_id = undefined;
          changed = true;
        }
      } else if (!requiresDistrict) {
        if (next.district_id) {
          next.district_id = undefined;
          changed = true;
        }
        if (next.subdistrict_id) {
          next.subdistrict_id = undefined;
          changed = true;
        }
        if (next.health_service_id) {
          next.health_service_id = undefined;
          changed = true;
        }
      } else if (!requiresSubdistrict) {
        if (next.subdistrict_id) {
          next.subdistrict_id = undefined;
          changed = true;
        }
        if (next.health_service_id) {
          next.health_service_id = undefined;
          changed = true;
        }
      }

      if (!requiresHealthArea && next.health_area_id) {
        next.health_area_id = undefined;
        changed = true;
      }

      if (!requiresVillageCode && next.area_code) {
        next.area_code = undefined;
        changed = true;
      }

      return changed ? next : prev;
    });

    if (!requiresProvince) {
      setDistricts([]);
      setSubdistricts([]);
      setHealthServices([]);
      return;
    }
    if (!requiresDistrict) {
      setSubdistricts([]);
      setHealthServices([]);
      return;
    }
    if (!requiresSubdistrict) {
      setHealthServices([]);
    }
  }, [
    lockedAreaScope,
    requiresProvince,
    requiresDistrict,
    requiresSubdistrict,
    requiresHealthArea,
    requiresVillageCode,
  ]);

  useEffect(() => {
    if (!enforcedDistrictId) {
      return;
    }
    setDistricts((prev) =>
      ensureLookupIncludes(prev, enforcedDistrictId, enforcedDistrictName),
    );
  }, [enforcedDistrictId, enforcedDistrictName]);

  useEffect(() => {
    if (!enforcedSubdistrictId) {
      return;
    }
    setSubdistricts((prev) =>
      ensureLookupIncludes(
        prev,
        enforcedSubdistrictId,
        enforcedSubdistrictName,
      ),
    );
  }, [enforcedSubdistrictId, enforcedSubdistrictName]);

  // Preload enforced districts once without looping on the loading flag.
  useEffect(() => {
    if (mode !== "create") {
      return;
    }
    if (!shouldLockProvince || !enforcedProvinceId) {
      return;
    }
    if (districts.length > 0 || isLoadingDistricts) {
      return;
    }
    lastDistrictFetchKey.current = enforcedProvinceId;
    let cancelled = false;
    const load = async () => {
      setIsLoadingDistricts(true);
      try {
        let items = await fetchDistricts(enforcedProvinceId);
        items = ensureLookupIncludes(
          items,
          enforcedDistrictId,
          enforcedDistrictName,
        );
        if (!cancelled) {
          setDistricts(items);
        }
      } catch (error) {
        if (!cancelled) {
          setDistricts([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingDistricts(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
      setIsLoadingDistricts(false);
    };
  }, [mode, shouldLockProvince, enforcedProvinceId, districts.length]);

  // Preload enforced subdistricts in the same manner to avoid duplicate calls.
  useEffect(() => {
    if (mode !== "create") {
      return;
    }
    if (!shouldLockDistrict || !enforcedDistrictId) {
      return;
    }
    if (subdistricts.length > 0 || isLoadingSubdistricts) {
      return;
    }
    lastSubdistrictFetchKey.current = enforcedDistrictId;
    let cancelled = false;
    const load = async () => {
      setIsLoadingSubdistricts(true);
      try {
        let items = await fetchSubdistricts(enforcedDistrictId);
        items = ensureLookupIncludes(
          items,
          enforcedSubdistrictId,
          enforcedSubdistrictName,
        );
        if (!cancelled) {
          setSubdistricts(items);
        }
      } catch (error) {
        if (!cancelled) {
          setSubdistricts([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSubdistricts(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
      setIsLoadingSubdistricts(false);
    };
  }, [mode, shouldLockDistrict, enforcedDistrictId, subdistricts.length]);

  useEffect(() => {
    const fetchKey = selectedProvince || null;
    if (!selectedProvince) {
      lastDistrictFetchKey.current = null;
      setDistricts([]);
      setSubdistricts([]);
      setIsLoadingDistricts(false);
      setIsLoadingSubdistricts(false);
      return;
    }

    if (
      lastDistrictFetchKey.current === fetchKey &&
      (districts.length > 0 || isLoadingDistricts)
    ) {
      return;
    }
    lastDistrictFetchKey.current = fetchKey;

    let cancelled = false;
    const loadDistricts = async () => {
      setIsLoadingDistricts(true);
      try {
        let items = await fetchDistricts(selectedProvince);
        if (!cancelled && districtFallback) {
          if (!items.some((item) => item.id === districtFallback.id)) {
            items = [districtFallback, ...items];
          }
        }
        items = ensureLookupIncludes(
          items,
          enforcedDistrictId,
          enforcedDistrictName,
        );
        if (!cancelled) {
          setDistricts(items);
        }
      } catch (error) {
        if (!cancelled) {
          setDistricts([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingDistricts(false);
        }
      }
    };

    loadDistricts();
    return () => {
      cancelled = true;
      setIsLoadingDistricts(false);
    };
  }, [selectedProvince, districtFallback]);

  useEffect(() => {
    const fetchKey = selectedDistrict || null;
    if (!selectedDistrict) {
      lastSubdistrictFetchKey.current = null;
      setSubdistricts([]);
      setIsLoadingSubdistricts(false);
      return;
    }

    if (
      lastSubdistrictFetchKey.current === fetchKey &&
      (subdistricts.length > 0 || isLoadingSubdistricts)
    ) {
      return;
    }
    lastSubdistrictFetchKey.current = fetchKey;

    let cancelled = false;
    const loadSubdistricts = async () => {
      setIsLoadingSubdistricts(true);
      try {
        let items = await fetchSubdistricts(selectedDistrict);
        if (!cancelled && subdistrictFallback) {
          if (!items.some((item) => item.id === subdistrictFallback.id)) {
            items = [subdistrictFallback, ...items];
          }
        }
        items = ensureLookupIncludes(
          items,
          enforcedSubdistrictId,
          enforcedSubdistrictName,
        );
        if (!cancelled) {
          setSubdistricts(items);
        }
      } catch (error) {
        if (!cancelled) {
          setSubdistricts([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSubdistricts(false);
        }
      }
    };

    loadSubdistricts();
    return () => {
      cancelled = true;
      setIsLoadingSubdistricts(false);
    };
  }, [selectedDistrict, subdistrictFallback]);

  useEffect(() => {
    if (!requiresHealthService) {
      setHealthServices([]);
      setIsLoadingHealthServices(false);
      setFormValues((prev: CombinedFormValues) => ({
        ...prev,
        health_service_id: undefined,
      }));
      setHealthServiceError(null);
      return;
    }

    if (!selectedSubdistrict) {
      setHealthServices([]);
      setIsLoadingHealthServices(false);
      setFormValues((prev: CombinedFormValues) => ({
        ...prev,
        health_service_id: undefined,
      }));
      setHealthServiceError(null);
      return;
    }

    let cancelled = false;
    const loadHealthServices = async () => {
      setIsLoadingHealthServices(true);
      try {
        let items = await fetchHealthServices({
          provinceCode: selectedProvince || undefined,
          districtCode: selectedDistrict || undefined,
          subdistrictCode: selectedSubdistrict || undefined,
        });
        if (!cancelled && healthServiceFallback) {
          if (!items.some((item) => item.id === healthServiceFallback.id)) {
            items = [healthServiceFallback, ...items];
          }
        }
        if (!cancelled && enforcedHealthServiceId) {
          items = ensureLookupIncludes(
            items,
            enforcedHealthServiceId,
            enforcedHealthServiceName ?? undefined,
          );
        }
        if (!cancelled) {
          setHealthServices(items);
        }
      } catch (error) {
        if (!cancelled) {
          setHealthServices([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHealthServices(false);
        }
      }
    };

    loadHealthServices();
    return () => {
      cancelled = true;
      setIsLoadingHealthServices(false);
    };
  }, [
    requiresHealthService,
    selectedProvince,
    selectedDistrict,
    selectedSubdistrict,
    healthServiceFallback,
    enforcedHealthServiceId,
    enforcedHealthServiceName,
  ]);

  useEffect(() => {
    if (mode !== "create") {
      return;
    }
    if (!requiresHealthService || !enforcedHealthServiceId) {
      return;
    }
    if (formValues.health_service_id === enforcedHealthServiceId) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      health_service_id: enforcedHealthServiceId,
    }));
  }, [
    mode,
    requiresHealthService,
    enforcedHealthServiceId,
    formValues.health_service_id,
  ]);

  useEffect(() => {
    if (mode !== "create") {
      return;
    }
    if (!requiresHealthArea || !enforcedHealthAreaId) {
      return;
    }
    const resolvedOption = healthAreaSelectOptions.find((option) =>
      isSameHealthAreaCode(option.value, enforcedHealthAreaId),
    );
    const targetValue = resolvedOption?.value ?? enforcedHealthAreaId;
    const currentValue =
      typeof formValues.health_area_id === "string"
        ? formValues.health_area_id
        : "";
    if (currentValue === targetValue) {
      return;
    }
    if (
      currentValue &&
      isSameHealthAreaCode(currentValue, targetValue) &&
      !resolvedOption
    ) {
      return;
    }
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      health_area_id: targetValue,
    }));
  }, [
    mode,
    requiresHealthArea,
    enforcedHealthAreaId,
    healthAreaSelectOptions,
    formValues.health_area_id,
  ]);

  const handleBirthDateSelect = (date: Date | null) => {
    setSelectedBirthDate(date);
    setFormValues((prev: CombinedFormValues) => ({
      ...prev,
      birth_date: dateToIso(date),
    }));
    setBirthDateError(null);
  };

  return (
    <form className="space-y-8" onSubmit={handleSubmit}>
      <fieldset className="space-y-8" disabled={isSubmitting}>
        {mode === "create" && (
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              เลขประจำตัวประชาชน <span className="text-red-500">*</span>
            </label>
            <input
              value={(formValues.citizen_id as string) ?? ""}
              onChange={handleChange("citizen_id")}
              placeholder="กรอกเลขประจำตัวประชาชน"
              maxLength={13}
              required
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              คำนำหน้า <span className="text-red-500">*</span>
            </label>
            <Select
              inputId="prefix_id"
              options={prefixSelectOptions}
              value={findOption(
                prefixSelectOptions,
                formValues.prefix_id as string,
              )}
              onChange={(option) =>
                setFormValues((prev: CombinedFormValues) => ({
                  ...prev,
                  prefix_id: option?.value ?? "",
                }))
              }
              placeholder="เลือกคำนำหน้า"
              isClearable
              isSearchable
              styles={selectStyles}
              classNamePrefix="rs"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              ชื่อ <span className="text-red-500">*</span>
            </label>
            <input
              value={(formValues.first_name as string) ?? ""}
              onChange={handleChange("first_name")}
              required
              placeholder="กรอกชื่อ"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              นามสกุล <span className="text-red-500">*</span>
            </label>
            <input
              value={(formValues.last_name as string) ?? ""}
              onChange={handleChange("last_name")}
              required
              placeholder="กรอกนามสกุล"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              เพศ
            </label>
            <Select
              inputId="gender"
              options={genderSelectOptions}
              value={findOption(
                genderSelectOptions,
                formValues.gender as string,
              )}
              onChange={(option) =>
                setFormValues((prev: CombinedFormValues) => ({
                  ...prev,
                  gender: option?.value ?? "",
                }))
              }
              placeholder="เลือกเพศ"
              isClearable
              isSearchable
              styles={selectStyles}
              classNamePrefix="rs"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              วันเดือนปีเกิด
            </label>
            <DatePicker
              selected={selectedBirthDate}
              onChange={(value) => {
                const nextValue = Array.isArray(value)
                  ? (value[0] ?? null)
                  : (value ?? null);
                handleBirthDateSelect(nextValue);
              }}
              customInput={
                <ThaiDateInput placeholder="วัน/เดือน/ปี พ.ศ. (เช่น 25/12/2523)" />
              }
              dateFormat="dd/MM/yyyy"
              locale="th"
              renderCustomHeader={(props) =>
                renderThaiHeader({
                  ...props,
                  availableYears,
                })
              }
              calendarStartDay={0}
              maxDate={maxSelectableBirthDate}
              popperPlacement="bottom-start"
              shouldCloseOnSelect
              disabled={isSubmitting}
            />
            {birthDateError && (
              <p className="text-xs font-medium text-rose-600">
                {birthDateError}
              </p>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              เบอร์โทรศัพท์
            </label>
            <input
              value={(formValues.phone as string) ?? ""}
              onChange={handleChange("phone")}
              placeholder="กรอกเบอร์โทรศัพท์"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              อีเมล
            </label>
            <input
              type="email"
              value={(formValues.email as string) ?? ""}
              onChange={handleChange("email")}
              placeholder="name@example.com"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            ตำแหน่งและสิทธิ์
          </h3>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-700">
                ตำแหน่ง <span className="text-red-500">*</span>
              </label>
              <Select
                inputId="position_id"
                options={positionSelectOptions}
                value={findOption(
                  positionSelectOptions,
                  formValues.position_id as string,
                )}
                onChange={(option) => {
                  setFormValues((prev: CombinedFormValues) => ({
                    ...prev,
                    position_id: option?.value ?? "",
                  }));
                  setPositionError(null);
                }}
                placeholder="เลือกตำแหน่ง"
                isClearable
                isSearchable
                isDisabled={isSubmitting}
                noOptionsMessage={() =>
                  loadingMeta
                    ? "กำลังโหลดข้อมูลตำแหน่ง…"
                    : "ไม่พบตำแหน่งที่เลือกได้"
                }
                styles={selectStyles}
                classNamePrefix="rs"
              />
              {loadingMeta && (
                <p className="text-xs text-slate-500">
                  กำลังโหลดข้อมูลตำแหน่ง…
                </p>
              )}
              {!loadingMeta &&
                isPositionSelectionDisabled &&
                userScopeLabel && (
                  <p className="text-xs font-semibold text-rose-600">
                    บัญชีของคุณสามารถสร้างได้เฉพาะตำแหน่งที่ไม่สูงกว่าระดับ
                    {userScopeLabel} กรุณาติดต่อผู้ดูแลเพื่อขอสิทธิ์เพิ่มเติม
                  </p>
                )}
              {!loadingMeta &&
                hasPositionRestriction &&
                !isPositionSelectionDisabled &&
                userScopeLabel &&
                userScopeLabel !== SCOPE_LABELS.country && (
                  <p className="text-xs text-slate-500">
                    แสดงเฉพาะตำแหน่งที่ไม่สูงกว่าระดับ{userScopeLabel}
                  </p>
                )}
              {positionError && (
                <p className="text-xs font-medium text-rose-600">
                  {positionError}
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-700">
                บ้านเลขที่
              </label>
              <input
                value={(formValues.address_number as string) ?? ""}
                onChange={handleChange("address_number")}
                placeholder="กรอกบ้านเลขที่"
                className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>
          </div>
        </div>

        {(requiresProvince || requiresDistrict || requiresSubdistrict) && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              พื้นที่รับผิดชอบ
            </h3>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {requiresProvince && (
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-slate-700">
                    จังหวัด
                  </label>
                  <Select
                    inputId="province_id"
                    options={provinceSelectOptions}
                    value={findOption(provinceSelectOptions, selectedProvince)}
                    onChange={(option) =>
                      handleProvinceChange(option?.value ?? "")
                    }
                    placeholder="เลือกจังหวัด"
                    isClearable
                    isSearchable
                    isDisabled={shouldLockProvince}
                    styles={selectStyles}
                    classNamePrefix="rs"
                  />
                  {showProvinceLoading && (
                    <p className="text-xs text-slate-500">
                      กำลังโหลดข้อมูลจังหวัด…
                    </p>
                  )}
                  {!showProvinceLoading && provincesError && (
                    <p className="text-xs font-semibold text-rose-600">
                      {provincesError}
                    </p>
                  )}
                  {shouldLockProvince &&
                    (enforcedProvinceName || enforcedProvinceId) && (
                      <p className="text-xs text-slate-500">
                        สิทธิ์ของคุณกำหนดเฉพาะจังหวัด
                        {enforcedProvinceName ?? enforcedProvinceId}
                      </p>
                    )}
                  {showAreaScopeProvinceHint && !shouldLockProvince && (
                    <p className="text-xs text-slate-500">
                      แสดงเฉพาะจังหวัดในเขตสุขภาพของคุณ
                    </p>
                  )}
                </div>
              )}
              {requiresDistrict && (
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-slate-700">
                    อำเภอ
                  </label>
                  <Select
                    inputId="district_id"
                    options={districtSelectOptions}
                    value={findOption(districtSelectOptions, selectedDistrict)}
                    onChange={(option) =>
                      handleDistrictChange(option?.value ?? "")
                    }
                    placeholder="เลือกอำเภอ"
                    isClearable
                    isSearchable
                    isDisabled={!selectedProvince || shouldLockDistrict}
                    styles={selectStyles}
                    classNamePrefix="rs"
                  />
                  {showDistrictLoading && (
                    <p className="text-xs text-slate-500">
                      กำลังโหลดข้อมูลอำเภอ…
                    </p>
                  )}
                  {shouldLockDistrict &&
                    (enforcedDistrictName || enforcedDistrictId) && (
                      <p className="text-xs text-slate-500">
                        สิทธิ์ของคุณจำกัดที่อำเภอ
                        {enforcedDistrictName ?? enforcedDistrictId}
                      </p>
                    )}
                </div>
              )}
              {requiresSubdistrict && (
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-semibold text-slate-700">
                    ตำบล
                  </label>
                  <Select
                    inputId="subdistrict_id"
                    options={subdistrictSelectOptions}
                    value={findOption(
                      subdistrictSelectOptions,
                      selectedSubdistrict,
                    )}
                    onChange={(option) =>
                      handleSubdistrictChange(option?.value ?? "")
                    }
                    placeholder="เลือกตำบล"
                    isClearable
                    isSearchable
                    isDisabled={!selectedDistrict || shouldLockSubdistrict}
                    styles={selectStyles}
                    classNamePrefix="rs"
                  />
                  {showSubdistrictLoading && (
                    <p className="text-xs text-slate-500">
                      กำลังโหลดข้อมูลตำบล…
                    </p>
                  )}
                  {shouldLockSubdistrict &&
                    (enforcedSubdistrictName || enforcedSubdistrictId) && (
                      <p className="text-xs text-slate-500">
                        สิทธิ์ของคุณจำกัดที่ตำบล
                        {enforcedSubdistrictName ?? enforcedSubdistrictId}
                      </p>
                    )}
                </div>
              )}
            </div>
          </div>
        )}

        {requiresSubdistrict && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-700">
                หน่วยบริการสุขภาพ{" "}
                {requiresHealthService && (
                  <span className="text-red-500">*</span>
                )}
              </label>
              <Select
                inputId="health_service_id"
                options={healthServiceSelectOptions}
                value={findOption(
                  healthServiceSelectOptions,
                  formValues.health_service_id as string,
                )}
                onChange={(option) => {
                  setFormValues((prev: CombinedFormValues) => ({
                    ...prev,
                    health_service_id: option?.value ?? "",
                  }));
                  setHealthServiceError(null);
                }}
                placeholder={
                  isLoadingHealthServices
                    ? "กำลังโหลด..."
                    : "เลือกหน่วยบริการสุขภาพ"
                }
                isClearable
                isSearchable
                isDisabled={
                  shouldLockHealthService ||
                  !selectedSubdistrict ||
                  isLoadingHealthServices ||
                  healthServices.length === 0
                }
                styles={selectStyles}
                classNamePrefix="rs"
              />
              {!selectedSubdistrict && (
                <p className="text-xs text-slate-500">
                  กรุณาเลือกตำบลก่อนเพื่อแสดงหน่วยบริการสุขภาพ
                </p>
              )}
              {selectedSubdistrict &&
                !isLoadingHealthServices &&
                healthServices.length === 0 && (
                  <p className="text-xs text-slate-500">
                    ไม่พบหน่วยบริการสุขภาพในพื้นที่ที่เลือก
                  </p>
                )}
              {shouldLockHealthService && enforcedHealthServiceId && (
                <p className="text-xs text-slate-500">
                  สิทธิ์ของคุณจำกัดที่หน่วยบริการสุขภาพ{" "}
                  {enforcedHealthServiceName ?? enforcedHealthServiceId}
                </p>
              )}
              {healthServiceError && (
                <p className="text-xs font-medium text-rose-600">
                  {healthServiceError}
                </p>
              )}
            </div>
          </div>
        )}

        {requiresHealthArea && (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-slate-700">
                เขตสุขภาพ
              </label>
              <Select
                inputId="health_area_id"
                options={healthAreaSelectOptions}
                value={findOption(
                  healthAreaSelectOptions,
                  selectedHealthAreaValue,
                )}
                onChange={(option) =>
                  setFormValues((prev: CombinedFormValues) => ({
                    ...prev,
                    health_area_id: option?.value ?? "",
                  }))
                }
                placeholder="เลือกเขตสุขภาพ"
                isClearable
                isSearchable
                isDisabled={
                  shouldLockHealthArea ||
                  (loadingMeta && healthAreas.length === 0)
                }
                styles={selectStyles}
                classNamePrefix="rs"
              />
              {loadingMeta && healthAreas.length === 0 && (
                <p className="text-xs text-slate-500">
                  กำลังโหลดข้อมูลเขตสุขภาพ…
                </p>
              )}
              {shouldLockHealthArea && enforcedHealthAreaLabel && (
                <p className="text-xs text-slate-500">
                  สิทธิ์ของคุณกำหนดเขตสุขภาพเป็น {enforcedHealthAreaLabel}
                </p>
              )}
            </div>
          </div>
        )}

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              หมู่ที่
            </label>
            <input
              value={(formValues.village_no as string) ?? ""}
              onChange={handleChange("village_no")}
              placeholder="กรอกหมู่ที่"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              ตรอก/ซอย
            </label>
            <input
              value={(formValues.alley as string) ?? ""}
              onChange={handleChange("alley")}
              placeholder="กรอกตรอก/ซอย"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">ถนน</label>
            <input
              value={(formValues.street as string) ?? ""}
              onChange={handleChange("street")}
              placeholder="กรอกถนน"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              รหัสไปรษณีย์
            </label>
            <input
              value={(formValues.postal_code as string) ?? ""}
              onChange={handleChange("postal_code")}
              placeholder="กรอกรหัสไปรษณีย์"
              className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
        </div>

        {mode === "create" && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-3">
              <label className="text-sm font-semibold text-slate-700">
                รหัสผ่านชั่วคราว <span className="text-red-500">*</span>
              </label>
              <button
                type="button"
                onClick={handleGeneratePassword}
                className="text-sm font-semibold text-blue-600 hover:text-blue-700"
              >
                สุ่มรหัสผ่าน 8 หลัก
              </button>
            </div>
            <PasswordInput
              value={(formValues.password as string) ?? ""}
              onChange={handleChange("password")}
              placeholder="กำหนดรหัสผ่านชั่วคราว"
              required
              minLength={8}
              autoComplete="new-password"
              inputClassName="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? "กำลังบันทึก…"
              : (submitLabel ??
                (mode === "create" ? "บันทึกข้อมูล" : "บันทึกการแก้ไข"))}
          </button>
        </div>
      </fieldset>
    </form>
  );
};
