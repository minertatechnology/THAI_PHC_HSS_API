import React, { useEffect, useMemo, useState } from "react";
import Select, { StylesConfig } from "react-select";
import { OfficerDetail, OfficerTransferPayload } from "../types/officer";
import {
  fetchDistricts,
  fetchHealthAreas,
  fetchHealthServices,
  fetchSubdistricts,
  LookupItem,
} from "../api/lookups";
import { useProvincesLookup } from "../hooks/useProvincesLookup";
import { useAuth } from "../hooks/useAuth";

export type OfficerTransferDialogProps = {
  open: boolean;
  officer: OfficerDetail | null;
  onClose: () => void;
  onSubmit: (payload: OfficerTransferPayload) => Promise<void>;
  busy?: boolean;
};

type SelectOption = { value: string; label: string };

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
    zIndex: 60,
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

const findOption = (
  options: SelectOption[],
  value?: string | null,
): SelectOption | null =>
  options.find((option) => option.value === value) ?? null;

export const OfficerTransferDialog: React.FC<OfficerTransferDialogProps> = ({
  open,
  officer,
  onClose,
  onSubmit,
  busy = false,
}) => {
  const { user } = useAuth();
  const {
    provinces,
    loading: loadingProvinces,
    error: provincesError,
  } = useProvincesLookup();
  const actorLevel = user?.permission_scope?.level ?? user?.position_scope_level ?? null;
  const scopeProvinceId =
    user?.permission_scope?.codes?.province_id ?? user?.province_code ?? null;
  const scopeDistrictId =
    user?.permission_scope?.codes?.district_id ?? user?.district_code ?? null;
  const scopeSubdistrictId = user?.permission_scope?.codes?.subdistrict_id ?? null;
  const scopeHealthServiceId =
    user?.permission_scope?.codes?.health_service_id ?? user?.health_service_id ?? null;
  const userPositionName = String(user?.position_name_th ?? "").trim();
  const isProvinceOperator =
    actorLevel === "province" ||
    (Boolean(userPositionName) &&
      userPositionName.includes("จังหวัด") &&
      !userPositionName.includes("อำเภอ") &&
      !userPositionName.includes("เขต") &&
      !userPositionName.includes("ภาค") &&
      !userPositionName.includes("ประเทศ"));
  const isDistrictOperator =
    user?.position_scope_level === "district" ||
    user?.permission_scope?.level === "district" ||
    (Boolean(userPositionName) &&
      userPositionName.includes("อำเภอ") &&
      !userPositionName.includes("จังหวัด") &&
      !userPositionName.includes("เขต") &&
      !userPositionName.includes("ภาค") &&
      !userPositionName.includes("ประเทศ"));
  const isSubdistrictOrLowerOperator =
    actorLevel === "subdistrict" ||
    actorLevel === "village" ||
    user?.position_scope_level === "subdistrict" ||
    user?.position_scope_level === "village" ||
    userPositionName.includes("รพ.สต") ||
    userPositionName.includes("รพสต");

  const lockProvinceSelection =
    isProvinceOperator || isDistrictOperator || isSubdistrictOrLowerOperator;
  const lockDistrictSelection =
    isDistrictOperator || isSubdistrictOrLowerOperator;
  const lockSubdistrictSelection = isSubdistrictOrLowerOperator;
  const lockHealthServiceSelection = isSubdistrictOrLowerOperator;
  const lockTransferAction = isSubdistrictOrLowerOperator;
  const [districts, setDistricts] = useState<LookupItem[]>([]);
  const [subdistricts, setSubdistricts] = useState<LookupItem[]>([]);
  const [healthAreas, setHealthAreas] = useState<LookupItem[]>([]);
  const [healthServices, setHealthServices] = useState<LookupItem[]>([]);
  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [loadingSubdistricts, setLoadingSubdistricts] = useState(false);
  const [loadingHealthAreas, setLoadingHealthAreas] = useState(false);
  const [loadingHealthServices, setLoadingHealthServices] = useState(false);
  const [healthAreaId, setHealthAreaId] = useState<string>("");
  const [provinceId, setProvinceId] = useState<string>("");
  const [districtId, setDistrictId] = useState<string>("");
  const [subdistrictId, setSubdistrictId] = useState<string>("");
  const [healthServiceId, setHealthServiceId] = useState<string>("");
  const [note, setNote] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !officer) {
      return;
    }
    setHealthAreaId(officer.health_area_id ?? "");
    setProvinceId(officer.province_id ?? "");
    setDistrictId(officer.district_id ?? "");
    setSubdistrictId(officer.subdistrict_id ?? "");
    setHealthServiceId(officer.health_service_id ?? "");
    setNote("");
    setError(null);
    if (officer.area_type === "province") {
      setDistrictId("");
      setSubdistrictId("");
      setHealthServiceId("");
    } else if (officer.area_type === "district") {
      setSubdistrictId("");
      setHealthServiceId("");
    }
  }, [open, officer]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (lockProvinceSelection && scopeProvinceId) {
      setProvinceId(scopeProvinceId);
    }
    if (lockDistrictSelection && scopeDistrictId) {
      setDistrictId(scopeDistrictId);
    }
    if (lockSubdistrictSelection && scopeSubdistrictId) {
      setSubdistrictId(scopeSubdistrictId);
    }
    if (lockHealthServiceSelection && scopeHealthServiceId) {
      setHealthServiceId(scopeHealthServiceId);
    }
  }, [
    open,
    lockProvinceSelection,
    lockDistrictSelection,
    lockSubdistrictSelection,
    lockHealthServiceSelection,
    scopeProvinceId,
    scopeDistrictId,
    scopeSubdistrictId,
    scopeHealthServiceId,
  ]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setLoadingHealthAreas(true);
    fetchHealthAreas()
      .then(setHealthAreas)
      .catch(() => setHealthAreas([]))
      .finally(() => setLoadingHealthAreas(false));
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!provinceId) {
      setDistricts([]);
      setSubdistricts([]);
      setHealthServices([]);
      return;
    }
    setLoadingDistricts(true);
    fetchDistricts(provinceId)
      .then(setDistricts)
      .catch(() => setDistricts([]))
      .finally(() => setLoadingDistricts(false));
  }, [open, provinceId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!districtId) {
      setSubdistricts([]);
      setHealthServices([]);
      return;
    }
    setLoadingSubdistricts(true);
    fetchSubdistricts(districtId)
      .then(setSubdistricts)
      .catch(() => setSubdistricts([]))
      .finally(() => setLoadingSubdistricts(false));
  }, [open, districtId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (!subdistrictId) {
      setHealthServices([]);
      return;
    }
    setLoadingHealthServices(true);
    fetchHealthServices({ subdistrictCode: subdistrictId, limit: 200 })
      .then(setHealthServices)
      .catch(() => setHealthServices([]))
      .finally(() => setLoadingHealthServices(false));
  }, [open, subdistrictId]);

  const provinceOptions = useMemo(
    () => {
      const scopeLevel = user?.permission_scope?.level;
      const codes = user?.permission_scope?.codes;
      const scopeHealthAreaId = codes?.health_area_id ?? user?.health_area_code ?? null;
      const scopeProvinceId = codes?.province_id ?? user?.province_code ?? null;
      const scopeRegionCode = codes?.region_code ?? user?.region_code ?? null;

      let scoped = provinces;
      if (scopeLevel === "region" && scopeRegionCode) {
        scoped = provinces.filter((item) => (item.region_code ?? null) === scopeRegionCode);
      } else if (scopeLevel === "area" && scopeHealthAreaId) {
        scoped = provinces.filter((item) => (item.health_area_id ?? null) === scopeHealthAreaId);
      } else if (
        (scopeLevel === "province" || scopeLevel === "district" || scopeLevel === "subdistrict" || scopeLevel === "village") &&
        scopeProvinceId
      ) {
        scoped = provinces.filter((item) => (resolveLookupValue(item) ?? "") === scopeProvinceId);
      }

      return createLookupOptions(scoped);
    },
    [provinces, user],
  );
  const districtOptions = useMemo(
    () => {
      if (lockDistrictSelection && scopeDistrictId) {
        return createLookupOptions(
          districts.filter(
            (item) => (resolveLookupValue(item) ?? "") === scopeDistrictId,
          ),
        );
      }
      return createLookupOptions(districts);
    },
    [districts, lockDistrictSelection, scopeDistrictId],
  );
  const healthAreaOptions = useMemo(
    () => {
      const scopeLevel = user?.permission_scope?.level;
      const scopeHealthAreaId = user?.permission_scope?.codes?.health_area_id ?? user?.health_area_code ?? null;
      if (scopeLevel === "area" && scopeHealthAreaId) {
        return createLookupOptions(
          healthAreas.filter((item) => (resolveLookupValue(item) ?? "") === scopeHealthAreaId),
        );
      }
      return createLookupOptions(healthAreas);
    },
    [healthAreas, user],
  );
  const subdistrictOptions = useMemo(() => {
    if (lockSubdistrictSelection && scopeSubdistrictId) {
      return createLookupOptions(
        subdistricts.filter(
          (item) => (resolveLookupValue(item) ?? "") === scopeSubdistrictId,
        ),
      );
    }
    return createLookupOptions(subdistricts);
  }, [subdistricts, lockSubdistrictSelection, scopeSubdistrictId]);
  const healthServiceOptions = useMemo(() => {
    if (lockHealthServiceSelection && scopeHealthServiceId) {
      return createLookupOptions(
        healthServices.filter(
          (item) => (resolveLookupValue(item) ?? "") === scopeHealthServiceId,
        ),
      );
    }
    return createLookupOptions(healthServices);
  }, [healthServices, lockHealthServiceSelection, scopeHealthServiceId]);

  if (!open || !officer) {
    return null;
  }

  const requiresProvince =
    officer.area_type === "province" ||
    officer.area_type === "district" ||
    officer.area_type === "subdistrict";
  const requiresHealthArea = officer.area_type === "area";
  const requiresDistrict =
    officer.area_type === "district" || officer.area_type === "subdistrict";
  const requiresSubdistrict = officer.area_type === "subdistrict";
  const requiresHealthService = officer.area_type === "subdistrict";

  const handleSubmit = async () => {
    setError(null);
    if (requiresHealthArea && !healthAreaId) {
      setError("กรุณาเลือกเขตสุขภาพ");
      return;
    }
    if (requiresProvince && !provinceId) {
      setError("กรุณาเลือกจังหวัด");
      return;
    }
    if (requiresDistrict && (!provinceId || !districtId)) {
      setError("กรุณาเลือกจังหวัดและอำเภอ");
      return;
    }
    if (
      requiresSubdistrict &&
      (!provinceId || !districtId || !subdistrictId || !healthServiceId)
    ) {
      setError("กรุณาเลือกจังหวัด อำเภอ ตำบล และหน่วยบริการสุขภาพ");
      return;
    }
    await onSubmit({
      health_area_id: requiresHealthArea ? healthAreaId || null : null,
      province_id: requiresProvince ? provinceId || null : null,
      district_id: requiresDistrict ? districtId || null : null,
      subdistrict_id: requiresSubdistrict ? subdistrictId || null : null,
      health_service_id: requiresHealthService ? healthServiceId || null : null,
      note: note || null,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
      <div className="w-full max-w-2xl rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h3 className="text-lg font-semibold text-slate-800">
            โยกย้ายเจ้าหน้าที่
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-100"
          >
            ✕
          </button>
        </div>
        <div className="space-y-5 px-6 py-5">
          <div className="text-sm text-slate-600">
            กำลังโยกย้าย: {officer.prefix_name_th ?? ""}
            {officer.first_name} {officer.last_name}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {requiresHealthArea && (
              <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-slate-700">
                  เขตสุขภาพ
                </label>
                <Select
                  inputId="transfer-health-area"
                  options={healthAreaOptions}
                  value={findOption(healthAreaOptions, healthAreaId)}
                  onChange={(option) => setHealthAreaId(option?.value ?? "")}
                  placeholder="เลือกเขตสุขภาพ"
                  isClearable
                  isSearchable
                  isDisabled={busy}
                  styles={selectStyles}
                  classNamePrefix="rs"
                />
                {loadingHealthAreas && (
                  <p className="text-xs text-slate-500">
                    กำลังโหลดข้อมูลเขตสุขภาพ…
                  </p>
                )}
              </div>
            )}
            {requiresProvince && (
              <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-slate-700">
                  จังหวัด
                </label>
                <Select
                  inputId="transfer-province"
                  options={provinceOptions}
                  value={findOption(provinceOptions, provinceId)}
                  onChange={(option) => {
                    const value = option?.value ?? "";
                    const selectedLookup = provinces.find(
                      (item) => (resolveLookupValue(item) ?? "") === value,
                    );
                    setProvinceId(value);
                    if (selectedLookup?.health_area_id) {
                      setHealthAreaId(selectedLookup.health_area_id);
                    }
                    setDistrictId("");
                    setSubdistrictId("");
                    setHealthServiceId("");
                  }}
                  placeholder="เลือกจังหวัด"
                  isClearable={!lockProvinceSelection}
                  isSearchable
                  isDisabled={busy || lockProvinceSelection}
                  styles={selectStyles}
                  classNamePrefix="rs"
                />
                {loadingProvinces && (
                  <p className="text-xs text-slate-500">
                    กำลังโหลดข้อมูลจังหวัด…
                  </p>
                )}
                {!loadingProvinces && provincesError && (
                  <p className="text-xs font-semibold text-rose-600">
                    {provincesError}
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
                  inputId="transfer-district"
                  options={districtOptions}
                  value={findOption(districtOptions, districtId)}
                  onChange={(option) => {
                    const value = option?.value ?? "";
                    setDistrictId(value);
                    setSubdistrictId("");
                    setHealthServiceId("");
                  }}
                  placeholder="เลือกอำเภอ"
                  isClearable={!lockDistrictSelection}
                  isSearchable
                  isDisabled={!provinceId || busy || lockDistrictSelection}
                  styles={selectStyles}
                  classNamePrefix="rs"
                />
                {loadingDistricts && (
                  <p className="text-xs text-slate-500">
                    กำลังโหลดข้อมูลอำเภอ…
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
                  inputId="transfer-subdistrict"
                  options={subdistrictOptions}
                  value={findOption(subdistrictOptions, subdistrictId)}
                  onChange={(option) => {
                    const value = option?.value ?? "";
                    setSubdistrictId(value);
                    setHealthServiceId("");
                  }}
                  placeholder="เลือกตำบล"
                  isClearable={!lockSubdistrictSelection}
                  isSearchable
                  isDisabled={!districtId || busy || lockSubdistrictSelection}
                  styles={selectStyles}
                  classNamePrefix="rs"
                />
                {loadingSubdistricts && (
                  <p className="text-xs text-slate-500">กำลังโหลดข้อมูลตำบล…</p>
                )}
              </div>
            )}
            {requiresHealthService && (
              <div className="flex flex-col gap-2">
                <label className="text-sm font-semibold text-slate-700">
                  หน่วยบริการสุขภาพ
                </label>
                <Select
                  inputId="transfer-health-service"
                  options={healthServiceOptions}
                  value={findOption(healthServiceOptions, healthServiceId)}
                  onChange={(option) => setHealthServiceId(option?.value ?? "")}
                  placeholder="เลือกหน่วยบริการสุขภาพ"
                  isClearable={!lockHealthServiceSelection}
                  isSearchable
                  isDisabled={!subdistrictId || busy || lockHealthServiceSelection}
                  styles={selectStyles}
                  classNamePrefix="rs"
                />
                {loadingHealthServices && (
                  <p className="text-xs text-slate-500">
                    กำลังโหลดหน่วยบริการสุขภาพ…
                  </p>
                )}
              </div>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm font-semibold text-slate-700">
              หมายเหตุ (ถ้ามี)
            </label>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              className="w-full rounded-xl border border-slate-200 px-4 py-2 text-sm text-slate-700 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="ระบุเหตุผลการโยกย้าย"
            />
          </div>
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-600">
              {error}
            </div>
          )}
          {lockTransferAction && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
              ระดับสิทธิ์ของคุณถูกล็อกปลายทางการโยกย้าย ไม่สามารถเปลี่ยนพื้นที่ปลายทางได้
            </div>
          )}
        </div>
        <div className="flex justify-end gap-3 border-t border-slate-200 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-70"
          >
            ยกเลิก
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={busy || lockTransferAction}
            className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            บันทึกการโยกย้าย
          </button>
        </div>
      </div>
    </div>
  );
};
