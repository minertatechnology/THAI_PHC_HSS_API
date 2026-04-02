import React, {
  ChangeEvent,
  FormEvent,
  forwardRef,
  useEffect,
  useMemo,
  useState,
} from "react";
import DatePicker, {
  registerLocale,
  ReactDatePickerCustomHeaderProps,
} from "react-datepicker";
import Select, { StylesConfig } from "react-select";
import { th } from "date-fns/locale";
registerLocale("th", th);
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import {
  fetchOfficerRegistrationMeta,
  fetchRegistrationGenders,
  fetchRegistrationPrefixes,
  fetchRegistrationPositions,
  fetchRegistrationProvinces,
  fetchRegistrationDistricts,
  fetchRegistrationSubdistricts,
  fetchRegistrationMunicipalities,
  fetchRegistrationHealthServices,
  registerOfficer,
} from "../api/officers";
import { fetchAllowedRegistrationDomains } from "../api/oauthClients";
import { LookupItem } from "../api/lookups";
import {
  AdministrativeLevel,
  OfficerRegistrationMeta,
  OfficerRegistrationPayload,
} from "../types/officer";
import { PageLoader } from "../components/ui/PageLoader";
import PasswordInput from "../components/PasswordInput";

const defaultPayload: OfficerRegistrationPayload = {
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
  municipality_id: "",
  health_area_id: "",
  health_service_id: "",
  area_type: undefined,
  area_code: "",
  password: "",
};

const genderLabelMap: Record<string, string> = {
  male: "ชาย",
  female: "หญิง",
  other: "อื่น ๆ",
};

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

type SelectOption = { value: string; label: string };

const resolveLookupLabel = (item: LookupItem): string =>
  item.label ?? item.name_th ?? item.name_en ?? item.code ?? item.id ?? "";

const createLookupOptions = (items: LookupItem[]): SelectOption[] =>
  items
    .map((item) => ({
      value: item.id ?? item.code ?? "",
      label: resolveLookupLabel(item),
    }))
    .filter((option) => option.value);

const findOption = (
  options: SelectOption[],
  value?: string,
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

const isoToDate = (value?: string): Date | null => {
  if (!value) {
    return null;
  }
  const [yearRaw, monthRaw, dayRaw] = value
    .split("-")
    .map((part) => Number(part));
  if ([yearRaw, monthRaw, dayRaw].some((num) => Number.isNaN(num))) {
    return null;
  }
  const date = new Date(yearRaw, monthRaw - 1, dayRaw);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
};

const dateToIso = (date: Date | null): string => {
  if (!date) {
    return "";
  }
  return `${pad(date.getFullYear())}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
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

const getThaiDPrefillFromQuery = (): {
  citizen_id?: string;
  first_name?: string;
  last_name?: string;
} => {
  const params = new URLSearchParams(window.location.search);
  const source = (params.get("source") || "").trim().toLowerCase();
  if (source !== "thaid") {
    return {};
  }
  const citizenId = (params.get("citizen_id") || "").trim();
  const firstName = (params.get("first_name") || "").trim();
  const lastName = (params.get("last_name") || "").trim();
  return {
    citizen_id: citizenId || undefined,
    first_name: firstName || undefined,
    last_name: lastName || undefined,
  };
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

const resolveScope = (
  positions: LookupItem[],
  positionId: string,
): AdministrativeLevel | undefined => {
  const found = positions.find((item) => item.id === positionId);
  return (found?.scope_level as AdministrativeLevel | undefined) ?? undefined;
};

const filterAndSortRegisterPositions = (
  positions: LookupItem[],
): LookupItem[] => {
  const hiddenCodes = new Set(["DIR", "VIL"]);
  const scopeOrder: Record<string, number> = {
    village: 0,
    subdistrict: 1,
    district: 2,
    province: 3,
    area: 4,
    region: 5,
    country: 6,
  };
  return [...positions]
    .filter((item) => {
      const code = String(item.code ?? "").toUpperCase();
      const scope = String(item.scope_level ?? "").toLowerCase();
      return !hiddenCodes.has(code) && scope !== "village";
    })
    .sort((a, b) => {
      const aScope =
        scopeOrder[String(a.scope_level ?? "").toLowerCase()] ?? 999;
      const bScope =
        scopeOrder[String(b.scope_level ?? "").toLowerCase()] ?? 999;
      if (aScope !== bScope) {
        return aScope - bScope;
      }
      const aLabel = String(a.label ?? "");
      const bLabel = String(b.label ?? "");
      return aLabel.localeCompare(bLabel, "th");
    });
};

/**
 * Validates a return URL against a whitelist of allowed domains
 * to prevent open redirect vulnerabilities
 * @param url - The URL to validate
 * @param allowedDomains - List of allowed domains (fetched from OAuth clients)
 */
const isValidReturnUrl = (url: string, allowedDomains: string[]): boolean => {
  if (!url || !allowedDomains || allowedDomains.length === 0) return false;

  try {
    const parsedUrl = new URL(decodeURIComponent(url));

    return allowedDomains.some(
      (domain) =>
        parsedUrl.hostname === domain ||
        parsedUrl.hostname.endsWith(`.${domain}`),
    );
  } catch (e) {
    return false;
  }
};

/**
 * Gets the login URL with returnUrl parameter if available
 * If returnUrl is an external URL (different origin), redirect directly to it
 * Otherwise, go to local /login page with returnUrl parameter
 */
const getLoginUrl = (validatedReturnUrl: string | null): string => {
  // Try multiple sources in order: state, sessionStorage, URL query
  let returnUrl =
    validatedReturnUrl || sessionStorage.getItem("registrationReturnUrl");

  // If still not found, try to get from current URL query string
  if (!returnUrl) {
    const urlParams = new URLSearchParams(window.location.search);
    returnUrl = urlParams.get("returnUrl");
  }

  if (returnUrl) {
    try {
      const returnUrlObj = new URL(returnUrl);
      const currentOrigin = window.location.origin;

      // If returnUrl is external (different origin), redirect directly to it
      if (returnUrlObj.origin !== currentOrigin) {
        return returnUrl;
      }

      // If same origin, go to /login with returnUrl parameter
      return `/login?returnUrl=${encodeURIComponent(returnUrl)}`;
    } catch (e) {
      // If URL parsing fails, treat as relative path
      return `/login?returnUrl=${encodeURIComponent(returnUrl)}`;
    }
  }

  return "/login";
};

/**
 * Clean up registration returnUrl from sessionStorage and redirect
 * Call this when leaving registration page (back to login, success, error, etc.)
 */
const cleanUpAndRedirect = (url: string) => {
  // Clean up session storage
  sessionStorage.removeItem("registrationReturnUrl");

  // Check if it's an external URL or internal path
  try {
    const urlObj = new URL(url);
    // External URL - use window.location.href
    window.location.href = url;
  } catch (e) {
    // Internal path - use navigate (but still clean up first)
    window.location.href = url;
  }
};

export const OfficerRegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, clearSession } = useAuth();
  const [meta, setMeta] = useState<OfficerRegistrationMeta | null>(null);
  const [form, setForm] = useState<OfficerRegistrationPayload>(defaultPayload);
  const [districts, setDistricts] = useState<LookupItem[]>([]);
  const [subdistricts, setSubdistricts] = useState<LookupItem[]>([]);
  const [municipalities, setMunicipalities] = useState<LookupItem[]>([]);
  const [healthServices, setHealthServices] = useState<LookupItem[]>([]);
  const [loadingMeta, setLoadingMeta] = useState<boolean>(true);
  const [loadingDistricts, setLoadingDistricts] = useState<boolean>(false);
  const [loadingSubdistricts, setLoadingSubdistricts] =
    useState<boolean>(false);
  const [loadingHealthServices, setLoadingHealthServices] =
    useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [validatedReturnUrl, setValidatedReturnUrl] = useState<string | null>(
    null,
  );
  const [allowedDomains, setAllowedDomains] = useState<string[]>([]);

  useEffect(() => {
    const prefill = getThaiDPrefillFromQuery();
    if (!prefill.citizen_id && !prefill.first_name && !prefill.last_name) {
      return;
    }

    setForm((previous) => ({
      ...previous,
      citizen_id: prefill.citizen_id ?? previous.citizen_id,
      first_name: prefill.first_name ?? previous.first_name,
      last_name: prefill.last_name ?? previous.last_name,
    }));
  }, []);

  // Clear session if already authenticated to prevent login conflicts
  useEffect(() => {
    clearSession();
  }, [clearSession]);

  // Fetch allowed domains from public API and validate return URL
  useEffect(() => {
    let cancelled = false;

    const initializeReturnUrl = async () => {
      try {
        // Fetch allowed domains from public API (no authentication required)
        const domains = await fetchAllowedRegistrationDomains();

        if (!cancelled) {
          setAllowedDomains(domains);
          console.log("Allowed registration domains:", domains);

          // Parse and validate return URL
          const urlParams = new URLSearchParams(window.location.search);
          const returnUrl = urlParams.get("returnUrl");

          if (returnUrl && isValidReturnUrl(returnUrl, domains)) {
            const decodedUrl = decodeURIComponent(returnUrl);
            setValidatedReturnUrl(decodedUrl);
            sessionStorage.setItem("registrationReturnUrl", decodedUrl);
            console.log("Valid return URL:", decodedUrl);
          } else if (returnUrl) {
            console.warn(
              "Invalid return URL detected and rejected:",
              returnUrl,
            );
            console.warn("Allowed domains:", domains);
          }
        }
      } catch (error) {
        console.error("Failed to initialize return URL validation:", error);
      }
    };

    initializeReturnUrl();

    return () => {
      cancelled = true;
      // Clean up sessionStorage when component unmounts
      // This prevents returnUrl from persisting if user navigates away
      sessionStorage.removeItem("registrationReturnUrl");
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadMeta = async () => {
      setLoadingMeta(true);
      try {
        const [response, genders, prefixes, positions, provinces] =
          await Promise.all([
            fetchOfficerRegistrationMeta(),
            fetchRegistrationGenders(),
            fetchRegistrationPrefixes(),
            fetchRegistrationPositions(),
            fetchRegistrationProvinces(),
          ]);
        if (!cancelled) {
          const mergedPositions = positions.length
            ? positions
            : response.positions;
          setMeta({
            ...response,
            genders: genders.length ? genders : response.genders,
            prefixes: prefixes.length ? prefixes : response.prefixes,
            positions: filterAndSortRegisterPositions(mergedPositions),
            provinces: provinces.length ? provinces : response.provinces,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError("ไม่สามารถโหลดข้อมูลลงทะเบียนได้ กรุณาลองใหม่อีกครั้ง");
        }
      } finally {
        if (!cancelled) {
          setLoadingMeta(false);
        }
      }
    };

    loadMeta();
    return () => {
      cancelled = true;
    };
  }, []);

  const positionScope = useMemo<AdministrativeLevel | undefined>(() => {
    if (!meta) {
      return undefined;
    }
    if (!form.position_id) {
      return undefined;
    }
    return resolveScope(meta.positions, form.position_id);
  }, [meta, form.position_id]);

  useEffect(() => {
    if (positionScope !== "subdistrict") {
      setForm((prev) => ({
        ...prev,
        health_service_id: "",
      }));
      setHealthServices([]);
      return;
    }

    if (!form.subdistrict_id) {
      setHealthServices([]);
      return;
    }

    let cancelled = false;
    const loadHealthServices = async () => {
      setLoadingHealthServices(true);
      try {
        const items = await fetchRegistrationHealthServices({
          provinceCode: form.province_id || undefined,
          districtCode: form.district_id || undefined,
          subdistrictCode: form.subdistrict_id,
        });
        if (!cancelled) {
          setHealthServices(items);
        }
      } catch (err) {
        if (!cancelled) {
          setHealthServices([]);
        }
      } finally {
        if (!cancelled) {
          setLoadingHealthServices(false);
        }
      }
    };

    loadHealthServices();
    return () => {
      cancelled = true;
    };
  }, [positionScope, form.subdistrict_id, form.province_id, form.district_id]);

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
  const availableYears = useMemo(() => {
    const lowerBound = maxSelectableBirthYear - 120;
    const years: number[] = [];
    for (let year = maxSelectableBirthYear; year >= lowerBound; year -= 1) {
      years.push(year);
    }
    return years;
  }, [maxSelectableBirthYear]);

  const prefixOptions = useMemo(
    () => createLookupOptions(meta?.prefixes ?? []),
    [meta],
  );
  const genderOptions = useMemo<SelectOption[]>(
    () =>
      (meta?.genders ?? []).map((item) => ({
        value: item.code,
        label: item.label ?? genderLabelMap[item.code ?? ""] ?? item.code,
      })),
    [meta],
  );
  const positionOptions = useMemo(
    () => createLookupOptions(meta?.positions ?? []),
    [meta],
  );
  const provinceOptions = useMemo(
    () => createLookupOptions(meta?.provinces ?? []),
    [meta],
  );
  const districtOptions = useMemo(
    () => createLookupOptions(districts),
    [districts],
  );
  const subdistrictOptions = useMemo(
    () => createLookupOptions(subdistricts),
    [subdistricts],
  );
  const municipalityOptions = useMemo(
    () => createLookupOptions(municipalities),
    [municipalities],
  );
  const healthAreaOptions = useMemo(
    () => createLookupOptions(meta?.health_areas ?? []),
    [meta],
  );
  const healthServiceOptions = useMemo(
    () => createLookupOptions(healthServices),
    [healthServices],
  );

  const selectedBirthDate = useMemo(
    () => isoToDate(form.birth_date),
    [form.birth_date],
  );

  const handleBirthDateSelect = (value: Date | null) => {
    setForm((prev) => ({
      ...prev,
      birth_date: dateToIso(value),
    }));
  };

  const requiresProvince =
    positionScope &&
    ["province", "district", "subdistrict", "village"].includes(positionScope);
  const requiresDistrict =
    positionScope &&
    ["district", "subdistrict", "village"].includes(positionScope);
  const requiresSubdistrict =
    positionScope && ["subdistrict", "village"].includes(positionScope);
  const requiresHealthService = positionScope === "subdistrict";
  const requiresHealthArea = positionScope === "area";
  const requiresVillageCode = positionScope === "village";
  const showAddressFields = false;

  useEffect(() => {
    if (!positionScope) {
      return;
    }
    if (positionScope === "area") {
      setForm((prev) => ({
        ...prev,
        province_id: "",
        district_id: "",
        subdistrict_id: "",
        municipality_id: "",
        health_service_id: "",
        area_code: "",
      }));
      setDistricts([]);
      setSubdistricts([]);
      setMunicipalities([]);
      setHealthServices([]);
      return;
    }

    if (!requiresProvince) {
      setForm((prev) => ({
        ...prev,
        province_id: "",
        district_id: "",
        subdistrict_id: "",
        municipality_id: "",
        health_area_id: "",
        health_service_id: "",
        area_code: "",
      }));
      setDistricts([]);
      setSubdistricts([]);
      setMunicipalities([]);
      setHealthServices([]);
    }
  }, [positionScope, requiresProvince]);

  const handleInputChange =
    (field: keyof OfficerRegistrationPayload) =>
    (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const value = event.target.value;
      setForm((prev) => ({
        ...prev,
        [field]: value,
      }));
    };

  const handleCitizenIdChange = (event: ChangeEvent<HTMLInputElement>) => {
    const rawValue = event.target.value ?? "";
    const digitsOnly = rawValue.replace(/\D/g, "");
    const trimmed = digitsOnly.slice(0, 13);
    setForm((prev) => ({
      ...prev,
      citizen_id: trimmed,
    }));
  };

  const resetLocationHierarchy = ({
    province = false,
    district = false,
    subdistrict = false,
  }: {
    province?: boolean;
    district?: boolean;
    subdistrict?: boolean;
  }) => {
    setForm((prev) => ({
      ...prev,
      province_id: province ? "" : prev.province_id,
      district_id: province || district ? "" : prev.district_id,
      subdistrict_id:
        province || district || subdistrict ? "" : prev.subdistrict_id,
      municipality_id:
        province || district || subdistrict ? "" : prev.municipality_id,
      area_code: province || district || subdistrict ? "" : prev.area_code,
      health_service_id:
        province || district || subdistrict ? "" : prev.health_service_id,
    }));
    if (province) {
      setDistricts([]);
      setSubdistricts([]);
      setMunicipalities([]);
      setHealthServices([]);
    } else if (district) {
      setSubdistricts([]);
      setMunicipalities([]);
      setHealthServices([]);
    } else if (subdistrict) {
      setMunicipalities([]);
      setHealthServices([]);
    }
  };

  const handleProvinceChange = async (value: string) => {
    resetLocationHierarchy({ province: true });
    setForm((prev) => ({
      ...prev,
      province_id: value,
      health_area_id:
        prev.health_area_id ||
        meta?.provinces.find((item) => item.id === value)?.health_area_id ||
        "",
    }));
    if (!value) {
      return;
    }
    setLoadingDistricts(true);
    try {
      const items = await fetchRegistrationDistricts(value);
      setDistricts(items);
    } catch (err) {
      setDistricts([]);
    } finally {
      setLoadingDistricts(false);
    }
  };

  const handleDistrictChange = async (value: string) => {
    resetLocationHierarchy({ district: true });
    setForm((prev) => ({
      ...prev,
      district_id: value,
    }));
    if (!value) {
      return;
    }
    setLoadingSubdistricts(true);
    try {
      const items = await fetchRegistrationSubdistricts(value);
      setSubdistricts(items);
    } catch (err) {
      setSubdistricts([]);
    } finally {
      setLoadingSubdistricts(false);
    }
  };

  const handleSubdistrictChange = async (value: string) => {
    resetLocationHierarchy({ subdistrict: true });
    setForm((prev) => ({
      ...prev,
      subdistrict_id: value,
    }));
    if (!value) {
      return;
    }
    try {
      const items = await fetchRegistrationMunicipalities({
        subdistrictCode: value,
      });
      setMunicipalities(items);
    } catch (err) {
      setMunicipalities([]);
    }
  };

  const validateForm = (): string | null => {
    if (!form.citizen_id.trim()) {
      return "กรุณากรอกเลขบัตรประชาชน";
    }
    if (form.citizen_id.length !== 13) {
      return "เลขบัตรประชาชนต้องมี 13 หลัก";
    }
    if (!form.prefix_id) {
      return "กรุณาเลือกคำนำหน้า";
    }
    if (!form.first_name.trim() || !form.last_name.trim()) {
      return "กรุณากรอกชื่อและนามสกุล";
    }
    if (!form.gender) {
      return "กรุณาเลือกเพศ";
    }
    if (!form.birth_date) {
      return "กรุณาเลือกวันเกิด";
    }
    const birthDate = isoToDate(form.birth_date);
    if (!birthDate) {
      return "กรุณาเลือกวันเกิดให้ถูกต้อง";
    }
    if (birthDate > minimumAdultBirthDate) {
      return "อายุยังไม่ครบ 18 ปีบริบูรณ์ ไม่สามารถสมัครได้";
    }
    if (!form.position_id) {
      return "กรุณาเลือกตำแหน่ง";
    }
    if (showAddressFields && !form.address_number.trim()) {
      return "กรุณากรอกที่อยู่";
    }
    if (!positionScope) {
      return "ไม่สามารถระบุขอบเขตตำแหน่งได้ กรุณาเลือกตำแหน่งใหม่";
    }
    if (requiresProvince && !form.province_id) {
      return "กรุณาเลือกจังหวัดตามพื้นที่รับผิดชอบ";
    }
    if (requiresDistrict && !form.district_id) {
      return "กรุณาเลือกอำเภอ";
    }
    if (requiresSubdistrict && !form.subdistrict_id) {
      return "กรุณาเลือกตำบล";
    }
    if (requiresHealthService && !form.health_service_id) {
      return "กรุณาเลือกหน่วยบริการสุขภาพ";
    }
    if (requiresHealthArea && !form.health_area_id) {
      return "กรุณาเลือกเขตสุขภาพ";
    }
    if (requiresVillageCode && !form.area_code) {
      return "กรุณาใส่รหัสหมู่บ้านหรือรหัสพื้นที่";
    }
    if (!form.password || !confirmPassword) {
      return "กรุณากรอกรหัสผ่านและยืนยันรหัสผ่าน";
    }
    if (form.password.length < 8) {
      return "รหัสผ่านต้องมีความยาวอย่างน้อย 8 ตัวอักษร";
    }
    if (form.password !== confirmPassword) {
      return "รหัสผ่านและยืนยันรหัสผ่านไม่ตรงกัน";
    }
    return null;
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    const validationMessage = validateForm();
    if (validationMessage) {
      setError(validationMessage);
      return;
    }

    const payload: OfficerRegistrationPayload = {
      ...form,
      area_type: positionScope,
      area_code: requiresVillageCode ? form.area_code : "",
      health_area_id: requiresHealthArea
        ? form.health_area_id
        : form.health_area_id || "",
      health_service_id: requiresHealthService ? form.health_service_id : "",
      municipality_id: form.municipality_id || "",
    };

    if (!requiresVillageCode) {
      payload.area_code = "";
    }

    if (!requiresHealthArea && !form.health_area_id && meta) {
      const province = meta.provinces.find(
        (item) => item.id === form.province_id,
      );
      if (province?.health_area_id) {
        payload.health_area_id = province.health_area_id;
      }
    }

    setSubmitting(true);
    try {
      const response = await registerOfficer(payload);
      setSuccess(
        response.message ??
          "ส่งคำขอลงทะเบียนเรียบร้อย เราจะแจ้งผลทางอีเมลเมื่อได้รับการอนุมัติ",
      );
      setForm(defaultPayload);
      setConfirmPassword("");
      setDistricts([]);
      setSubdistricts([]);
      setMunicipalities([]);
      setHealthServices([]);
      window.setTimeout(() => {
        // Use return URL if available, otherwise default to /login
        const returnUrl =
          validatedReturnUrl || sessionStorage.getItem("registrationReturnUrl");

        if (returnUrl) {
          cleanUpAndRedirect(returnUrl);
        } else {
          cleanUpAndRedirect("/login");
        }
      }, 2500);
    } catch (err) {
      setError(
        "ไม่สามารถส่งคำขอลงทะเบียนได้ กรุณาตรวจสอบข้อมูลแล้วลองใหม่อีกครั้ง",
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingMeta) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4 py-12">
        <div className="mx-auto w-full max-w-2xl">
          <PageLoader message="กำลังเตรียมแบบฟอร์มลงทะเบียน" minHeight={320} />
        </div>
      </div>
    );
  }

  if (!meta) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4 py-12">
        <div className="mx-auto w-full max-w-xl rounded-2xl border border-white/70 bg-white/90 p-8 text-center shadow-xl backdrop-blur">
          <h1 className="text-2xl font-semibold text-slate-900">
            ไม่สามารถโหลดข้อมูลได้
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            กรุณารีเฟรชหน้าเพื่อลองใหม่อีกครั้ง หรือกลับไปยังหน้าเข้าสู่ระบบ
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
            >
              ลองใหม่อีกครั้ง
            </button>
            <button
              type="button"
              onClick={() =>
                cleanUpAndRedirect(getLoginUrl(validatedReturnUrl))
              }
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
            >
              กลับสู่หน้าเข้าสู่ระบบ
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4 py-12">
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => cleanUpAndRedirect(getLoginUrl(validatedReturnUrl))}
            className="text-sm font-semibold text-blue-600 transition hover:text-blue-700"
          >
            ← กลับสู่หน้าเข้าสู่ระบบ
          </button>
          <div className="inline-flex items-center gap-2 rounded-full bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-blue-700 shadow-sm">
            Thai HSS • Officer Registration
          </div>
        </div>

        <div className="rounded-2xl border border-white/70 bg-white/95 p-8 shadow-xl backdrop-blur">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-semibold text-slate-900">
              ลงทะเบียนเจ้าหน้าที่
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              กรอกข้อมูลตามจริง
              ระบบจะส่งคำขอให้ผู้ที่มีสิทธิ์ในพื้นที่ของคุณอนุมัติ
              ก่อนใช้งานระบบจะต้องได้รับการตรวจสอบข้อมูล
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            <section className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                ข้อมูลบัญชี
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="citizen_id"
                  >
                    เลขบัตรประชาชน
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="citizen_id"
                    value={form.citizen_id}
                    onChange={handleCitizenIdChange}
                    maxLength={13}
                    inputMode="numeric"
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    placeholder="เช่น 1XXXXXXXXXXXX"
                    required
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="prefix_id"
                  >
                    คำนำหน้า
                    <span className="text-red-500">*</span>
                  </label>
                  <Select
                    inputId="prefix_id"
                    options={prefixOptions}
                    value={findOption(prefixOptions, form.prefix_id)}
                    onChange={(option) =>
                      setForm((prev) => ({
                        ...prev,
                        prefix_id: option?.value ?? "",
                      }))
                    }
                    placeholder="เลือกคำนำหน้า"
                    isClearable
                    isSearchable
                    styles={selectStyles}
                    className="mt-1"
                    classNamePrefix="rs"
                    noOptionsMessage={() => "ไม่พบข้อมูล"}
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="first_name"
                  >
                    ชื่อ
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="first_name"
                    value={form.first_name}
                    onChange={handleInputChange("first_name")}
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    required
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="last_name"
                  >
                    นามสกุล
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="last_name"
                    value={form.last_name}
                    onChange={handleInputChange("last_name")}
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    required
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="gender"
                  >
                    เพศ
                    <span className="text-red-500">*</span>
                  </label>
                  <Select
                    inputId="gender"
                    options={genderOptions}
                    value={findOption(genderOptions, form.gender)}
                    onChange={(option) =>
                      setForm((prev) => ({
                        ...prev,
                        gender: option?.value ?? "",
                      }))
                    }
                    placeholder="เลือกเพศ"
                    isClearable
                    isSearchable
                    styles={selectStyles}
                    className="mt-1"
                    classNamePrefix="rs"
                    noOptionsMessage={() => "ไม่พบข้อมูล"}
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="birth_date"
                  >
                    วันเกิด
                    <span className="text-red-500">*</span>
                  </label>
                  <div className="mt-1">
                    <DatePicker
                      id="birth_date"
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
                      disabled={submitting}
                    />
                  </div>
                </div>
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                ข้อมูลการติดต่อ
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="email"
                  >
                    อีเมล
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={form.email}
                    onChange={handleInputChange("email")}
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    placeholder="example@email.com"
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="phone"
                  >
                    เบอร์โทรศัพท์
                  </label>
                  <input
                    id="phone"
                    value={form.phone}
                    onChange={handleInputChange("phone")}
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    placeholder="081-XXX-XXXX"
                  />
                </div>
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                ตำแหน่งและพื้นที่รับผิดชอบ
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="md:col-span-2">
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="position_id"
                  >
                    ตำแหน่ง
                    <span className="text-red-500">*</span>
                  </label>
                  <Select
                    inputId="position_id"
                    options={positionOptions}
                    value={findOption(positionOptions, form.position_id)}
                    onChange={(option) =>
                      setForm((prev) => ({
                        ...prev,
                        position_id: option?.value ?? "",
                      }))
                    }
                    placeholder="เลือกตำแหน่งภายในพื้นที่"
                    isClearable
                    isSearchable
                    styles={selectStyles}
                    className="mt-1"
                    classNamePrefix="rs"
                    noOptionsMessage={() => "ไม่พบข้อมูล"}
                  />
                  {positionScope && (
                    <p className="mt-2 text-xs text-slate-500">
                      ระบบกำหนดขอบเขตตำแหน่งนี้ในระดับ{" "}
                      <span className="font-semibold text-blue-600">
                        {positionScope}
                      </span>
                    </p>
                  )}
                </div>

                {showAddressFields && (
                  <>
                    <div>
                      <label
                        className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                        htmlFor="address_number"
                      >
                        ที่อยู่เลขที่
                      </label>
                      <input
                        id="address_number"
                        value={form.address_number}
                        onChange={handleInputChange("address_number")}
                        className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                        placeholder="เลขที่บ้าน"
                      />
                    </div>

                    <div>
                      <label
                        className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                        htmlFor="street"
                      >
                        ถนน
                      </label>
                      <input
                        id="street"
                        value={form.street}
                        onChange={handleInputChange("street")}
                        className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                        placeholder="ถ้ามี"
                      />
                    </div>

                    <div>
                      <label
                        className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                        htmlFor="alley"
                      >
                        ซอย
                      </label>
                      <input
                        id="alley"
                        value={form.alley}
                        onChange={handleInputChange("alley")}
                        className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                        placeholder="ถ้ามี"
                      />
                    </div>

                    <div>
                      <label
                        className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                        htmlFor="postal_code"
                      >
                        รหัสไปรษณีย์
                      </label>
                      <input
                        id="postal_code"
                        value={form.postal_code}
                        onChange={handleInputChange("postal_code")}
                        className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                        placeholder="เช่น 10110"
                      />
                    </div>
                  </>
                )}

                {requiresProvince && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="province_id"
                    >
                      จังหวัด
                      <span className="text-red-500">*</span>
                    </label>
                    <Select
                      inputId="province_id"
                      options={provinceOptions}
                      value={findOption(provinceOptions, form.province_id)}
                      onChange={(option) =>
                        handleProvinceChange(option?.value ?? "")
                      }
                      placeholder="เลือกจังหวัด"
                      isClearable
                      isSearchable
                      styles={selectStyles}
                      className="mt-1"
                      classNamePrefix="rs"
                      noOptionsMessage={() => "ไม่พบข้อมูล"}
                    />
                  </div>
                )}

                {requiresDistrict && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="district_id"
                    >
                      อำเภอ
                      <span className="text-red-500">*</span>
                    </label>
                    <Select
                      inputId="district_id"
                      options={districtOptions}
                      value={findOption(districtOptions, form.district_id)}
                      onChange={(option) =>
                        handleDistrictChange(option?.value ?? "")
                      }
                      placeholder={
                        loadingDistricts ? "กำลังโหลด..." : "เลือกอำเภอ"
                      }
                      isClearable
                      isSearchable
                      isDisabled={loadingDistricts || districts.length === 0}
                      styles={selectStyles}
                      className="mt-1"
                      classNamePrefix="rs"
                      noOptionsMessage={() => "ไม่พบข้อมูล"}
                    />
                  </div>
                )}

                {requiresSubdistrict && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="subdistrict_id"
                    >
                      ตำบล
                      <span className="text-red-500">*</span>
                    </label>
                    <Select
                      inputId="subdistrict_id"
                      options={subdistrictOptions}
                      value={findOption(
                        subdistrictOptions,
                        form.subdistrict_id,
                      )}
                      onChange={(option) =>
                        handleSubdistrictChange(option?.value ?? "")
                      }
                      placeholder={
                        loadingSubdistricts ? "กำลังโหลด..." : "เลือกตำบล"
                      }
                      isClearable
                      isSearchable
                      isDisabled={
                        loadingSubdistricts || subdistricts.length === 0
                      }
                      styles={selectStyles}
                      className="mt-1"
                      classNamePrefix="rs"
                      noOptionsMessage={() => "ไม่พบข้อมูล"}
                    />
                  </div>
                )}

                {requiresHealthService && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="health_service_id"
                    >
                      หน่วยบริการสุขภาพ
                      <span className="text-red-500">*</span>
                    </label>
                    <Select
                      inputId="health_service_id"
                      options={healthServiceOptions}
                      value={findOption(
                        healthServiceOptions,
                        form.health_service_id,
                      )}
                      onChange={(option) =>
                        setForm((prev) => ({
                          ...prev,
                          health_service_id: option?.value ?? "",
                        }))
                      }
                      placeholder={
                        loadingHealthServices
                          ? "กำลังโหลด..."
                          : "เลือกหน่วยบริการสุขภาพ"
                      }
                      isClearable
                      isSearchable
                      isDisabled={
                        !form.subdistrict_id ||
                        loadingHealthServices ||
                        healthServices.length === 0
                      }
                      styles={selectStyles}
                      className="mt-1"
                      classNamePrefix="rs"
                      noOptionsMessage={() => "ไม่พบข้อมูล"}
                    />
                    {!form.subdistrict_id && (
                      <p className="mt-1 text-xs text-slate-500">
                        กรุณาเลือกตำบลก่อนเพื่อแสดงหน่วยบริการสุขภาพ
                      </p>
                    )}
                    {form.subdistrict_id &&
                      !loadingHealthServices &&
                      healthServices.length === 0 && (
                        <p className="mt-1 text-xs text-slate-500">
                          ไม่พบหน่วยบริการสุขภาพในพื้นที่ที่เลือก
                        </p>
                      )}
                  </div>
                )}

                {requiresHealthArea && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="health_area_id"
                    >
                      เขตสุขภาพ
                      <span className="text-red-500">*</span>
                    </label>
                    <Select
                      inputId="health_area_id"
                      options={healthAreaOptions}
                      value={findOption(healthAreaOptions, form.health_area_id)}
                      onChange={(option) =>
                        setForm((prev) => ({
                          ...prev,
                          health_area_id: option?.value ?? "",
                        }))
                      }
                      placeholder="เลือกเขตสุขภาพ"
                      isClearable
                      isSearchable
                      styles={selectStyles}
                      className="mt-1"
                      classNamePrefix="rs"
                      noOptionsMessage={() => "ไม่พบข้อมูล"}
                    />
                  </div>
                )}

                {requiresVillageCode && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="area_code"
                    >
                      รหัสหมู่บ้าน/รหัสพื้นที่
                      <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="area_code"
                      value={form.area_code}
                      onChange={handleInputChange("area_code")}
                      className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                      placeholder="เช่น 01"
                      required
                    />
                  </div>
                )}

                {municipalities.length > 0 && (
                  <div>
                    <label
                      className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                      htmlFor="municipality_id"
                    >
                      เทศบาล (ถ้ามี)
                    </label>
                    <Select
                      inputId="municipality_id"
                      options={municipalityOptions}
                      value={findOption(
                        municipalityOptions,
                        form.municipality_id,
                      )}
                      onChange={(option) =>
                        setForm((prev) => ({
                          ...prev,
                          municipality_id: option?.value ?? "",
                        }))
                      }
                      placeholder="ไม่ระบุ"
                      isClearable
                      isSearchable
                      styles={selectStyles}
                      className="mt-1"
                      classNamePrefix="rs"
                      noOptionsMessage={() => "ไม่พบข้อมูล"}
                    />
                  </div>
                )}
              </div>
            </section>

            <section className="space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                ตั้งค่ารหัสผ่าน
              </h2>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="password"
                  >
                    รหัสผ่าน
                    <span className="text-red-500">*</span>
                  </label>
                  <PasswordInput
                    id="password"
                    autoComplete="new-password"
                    value={form.password}
                    onChange={handleInputChange("password")}
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    placeholder="อย่างน้อย 8 ตัวอักษร"
                    required
                  />
                </div>
                <div>
                  <label
                    className="text-xs font-semibold uppercase tracking-wide text-slate-500"
                    htmlFor="confirm_password"
                  >
                    ยืนยันรหัสผ่าน
                    <span className="text-red-500">*</span>
                  </label>
                  <PasswordInput
                    id="confirm_password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    className="mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                    placeholder="กรอกอีกครั้ง"
                    required
                  />
                </div>
              </div>
            </section>

            {error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600">
                {error}
              </div>
            )}

            {success && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                {success}
              </div>
            )}

            <div className="flex flex-col-reverse items-center justify-between gap-4 border-t border-slate-100 pt-6 sm:flex-row">
              <p className="text-xs text-slate-500">
                เจ้าหน้าที่ที่ได้รับการอนุมัติแล้วสามารถเข้าสู่ระบบได้ทันที
                หากมีข้อสงสัยกรุณาติดต่อผู้ดูแลระดับพื้นที่ของคุณ
              </p>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submitting ? "กำลังส่งคำขอ..." : "ส่งคำขอลงทะเบียน"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default OfficerRegisterPage;
