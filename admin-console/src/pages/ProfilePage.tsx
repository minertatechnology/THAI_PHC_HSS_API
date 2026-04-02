import React, { useEffect, useMemo, useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { changePassword } from "../api/auth";
import { PageLoader } from "../components/ui/PageLoader";
import { SensitiveValue, EyeIcon, EyeOffIcon } from "../components/ui/SensitiveValue";
import PasswordInput from "../components/PasswordInput";

const userTypeLabelMap: Record<string, string> = {
  officer: "เจ้าหน้าที่",
  osm: "อสม.",
  "yuwa-osm": "ยุวอสม.",
  yuwa_osm: "ยุวอสม.",
  people: "ประชาชน",
};

const scopeLabelMap: Record<string, string> = {
  country: "ระดับประเทศ",
  department: "ระดับกรม",
  region: "ระดับภาค",
  area: "ระดับเขตสุขภาพ",
  province: "ระดับจังหวัด",
  district: "ระดับอำเภอ",
  subdistrict: "ระดับตำบล",
  village: "ระดับหมู่บ้าน"
};

const formatThaiDate = (value?: string) => {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString("th-TH", {
    day: "numeric",
    month: "long",
    year: "numeric"
  });
};

const ProfilePage: React.FC = () => {
  const { user, refreshProfile, logout } = useAuth();
  const [isRefreshing, setRefreshing] = useState<boolean>(() => !user);
  const [passwordForm, setPasswordForm] = useState({ current: "", new: "", confirm: "" });
  const [changeBusy, setChangeBusy] = useState(false);
  const [changeError, setChangeError] = useState<string | null>(null);
  const [changeSuccess, setChangeSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!user) {
      setRefreshing(true);
      refreshProfile().finally(() => setRefreshing(false));
    }
  }, [user, refreshProfile]);

  const scopeLabel = useMemo(() => {
    if (!user?.position_scope_level) {
      return "-";
    }
    return scopeLabelMap[user.position_scope_level] ?? user.position_scope_level;
  }, [user?.position_scope_level]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshProfile();
    } finally {
      setRefreshing(false);
    }
  };

  const handlePasswordFieldChange = (field: "current" | "new" | "confirm") => (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setChangeError(null);
    setChangeSuccess(null);
    setPasswordForm((prev) => ({ ...prev, [field]: value }));
  };

  const handlePasswordSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setChangeError(null);
    setChangeSuccess(null);

    if (!passwordForm.current || !passwordForm.new) {
      setChangeError("กรุณากรอกรหัสผ่านเดิมและรหัสผ่านใหม่ให้ครบถ้วน");
      return;
    }
    if (passwordForm.new !== passwordForm.confirm) {
      setChangeError("รหัสผ่านใหม่และยืนยันรหัสผ่านไม่ตรงกัน");
      return;
    }
    if (passwordForm.new.length < 8) {
      setChangeError("รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 8 ตัวอักษร");
      return;
    }

    setChangeBusy(true);
    try {
      await changePassword({ old_password: passwordForm.current, new_password: passwordForm.new });
      setPasswordForm({ current: "", new: "", confirm: "" });
      setChangeSuccess("เปลี่ยนรหัสผ่านสำเร็จ ระบบจะออกจากระบบเพื่อให้เข้าสู่ระบบใหม่ด้วยรหัสผ่านล่าสุด");
      window.setTimeout(() => {
        logout().catch(() => undefined);
      }, 1500);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      let message = "ไม่สามารถเปลี่ยนรหัสผ่านได้ กรุณาลองใหม่";
      if (typeof detail === "string") {
        if (detail === "old_password_incorrect") {
          message = "รหัสผ่านเดิมไม่ถูกต้อง กรุณาลองใหม่";
        } else if (detail === "password_unchanged") {
          message = "รหัสผ่านใหม่ต้องแตกต่างจากรหัสผ่านเดิม";
        } else if (detail === "account_locked") {
          message = "คุณใส่รหัสผ่านเดิมผิดเกิน 10 ครั้ง บัญชีถูกพักใช้งาน โปรดติดต่อผู้ดูแลเพื่อรีเซ็ตรหัสผ่าน";
        } else if (detail === "password_not_set") {
          message = "บัญชีนี้ยังไม่ได้ตั้งรหัสผ่าน กรุณาติดต่อผู้ดูแลระบบ";
        }
      }
      setChangeError(message);
    } finally {
      setChangeBusy(false);
    }
  };

  if (!user) {
    return (
      <div className="py-6">
        {isRefreshing ? (
          <PageLoader message="กำลังโหลดข้อมูลโปรไฟล์" />
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="text-sm text-slate-600">ไม่พบข้อมูลผู้ใช้ โปรดลองรีเฟรชอีกครั้ง</p>
            <button
              onClick={handleRefresh}
              className="mt-4 inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
              disabled={isRefreshing}
            >
              รีเฟรชข้อมูล
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">โปรไฟล์ของฉัน</h1>
          <p className="text-sm text-slate-500">ตรวจสอบข้อมูลผู้ใช้และสิทธิ์การเข้าถึงของคุณ</p>
        </div>
        <button
          onClick={handleRefresh}
          className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
          disabled={isRefreshing}
        >
          {isRefreshing ? "กำลังโหลด…" : "รีเฟรชข้อมูล"}
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">ข้อมูลบัญชี</h2>
          <dl className="mt-4 space-y-3">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">ชื่อ-นามสกุล</dt>
              <dd className="col-span-2 text-slate-800">{user.name}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">เลขบัตรประชาชน</dt>
              <dd className="col-span-2 text-slate-800">
                <SensitiveValue
                  value={user.citizen_id}
                  className="inline-flex items-center gap-2"
                  valueClassName="font-mono text-sm text-slate-800"
                  buttonClassName="rounded-full border border-slate-200 p-1 text-slate-600 transition hover:border-slate-300 hover:bg-slate-100"
                  revealIcon={<EyeIcon />}
                  hideIcon={<EyeOffIcon />}
                />
              </dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">ประเภทผู้ใช้</dt>
              <dd className="col-span-2 text-slate-800">{user.user_type ? (userTypeLabelMap[user.user_type] ?? user.user_type) : "-"}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">ตำแหน่ง</dt>
              <dd className="col-span-2 text-slate-800">{user.position_name_th ?? "-"}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">ระดับสิทธิ์</dt>
              <dd className="col-span-2 text-slate-800">{scopeLabel}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">วันเกิด</dt>
              <dd className="col-span-2 text-slate-800">{formatThaiDate(user.birth_date)}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">อีเมล</dt>
              <dd className="col-span-2 text-slate-800">{user.email || "-"}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">เบอร์โทรศัพท์</dt>
              <dd className="col-span-2 text-slate-800">{user.phone || "-"}</dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">สถานะผู้ดูแล</dt>
              <dd className="col-span-2 text-slate-800">{user.is_admin ? "มีสิทธิ์ผู้ดูแล" : "ผู้ใช้งานทั่วไป"}</dd>
            </div>
          </dl>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">ข้อมูลพื้นที่รับผิดชอบ</h2>
          <dl className="mt-4 space-y-3">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">เขตสุขภาพ</dt>
              <dd className="col-span-2 text-slate-800">
                {user.health_area_name
                  ? `${user.health_area_name} (${user.health_area_code})`
                  : user.health_area_code ?? user.permission_scope?.codes?.health_area_id ?? "-"}
              </dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">ภาค</dt>
              <dd className="col-span-2 text-slate-800">
                {user.region_name
                  ? `${user.region_name} (${user.region_code})`
                  : user.region_code ?? user.permission_scope?.codes?.region_code ?? "-"}
              </dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">จังหวัด</dt>
              <dd className="col-span-2 text-slate-800">
                {user.province_name
                  ? `${user.province_name} (${user.province_code})`
                  : user.province_code ?? "-"}
              </dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">อำเภอ</dt>
              <dd className="col-span-2 text-slate-800">
                {user.district_name
                  ? `${user.district_name} (${user.district_code})`
                  : user.district_code ?? "-"}
              </dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">ตำบล</dt>
              <dd className="col-span-2 text-slate-800">
                {user.subdistrict_name
                  ? `${user.subdistrict_name} (${user.subdistrict_code})`
                  : user.subdistrict_code ?? "-"}
              </dd>
            </div>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <dt className="font-medium text-slate-500">รหัสพื้นที่</dt>
              <dd className="col-span-2 text-slate-800">{user.area_code ?? "-"}</dd>
            </div>
            {user.health_service_name_th && (
              <div className="grid grid-cols-3 gap-3 text-sm">
                <dt className="font-medium text-slate-500">สถานบริการสุขภาพ</dt>
                <dd className="col-span-2 text-slate-800">
                  {user.health_service_name_th}
                  {user.health_service_id ? ` (${user.health_service_id})` : ""}
                </dd>
              </div>
            )}
          </dl>
        </section>
      </div>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">จัดการรหัสผ่าน</h2>
        <p className="mt-2 text-sm text-slate-500">เปลี่ยนรหัสผ่านได้ด้วยตนเอง โดยต้องยืนยันรหัสผ่านเดิมก่อนทุกครั้ง</p>
        <form className="mt-5 space-y-4" onSubmit={handlePasswordSubmit}>
          <div className="grid gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor="current-password">
              รหัสผ่านปัจจุบัน
            </label>
            <PasswordInput
              id="current-password"
              autoComplete="current-password"
              value={passwordForm.current}
              onChange={handlePasswordFieldChange("current")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="กรอกรหัสผ่านที่ใช้งานอยู่"
              disabled={changeBusy}
            />
          </div>
          <div className="grid gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor="new-password">
              รหัสผ่านใหม่
            </label>
            <PasswordInput
              id="new-password"
              autoComplete="new-password"
              value={passwordForm.new}
              onChange={handlePasswordFieldChange("new")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="อย่างน้อย 8 ตัวอักษร ควรมีทั้งตัวอักษรและตัวเลข"
              disabled={changeBusy}
            />
          </div>
          <div className="grid gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor="confirm-password">
              ยืนยันรหัสผ่านใหม่
            </label>
            <PasswordInput
              id="confirm-password"
              autoComplete="new-password"
              value={passwordForm.confirm}
              onChange={handlePasswordFieldChange("confirm")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              placeholder="กรอกรหัสผ่านใหม่อีกครั้ง"
              disabled={changeBusy}
            />
          </div>

          {changeError && <p className="text-xs text-rose-600">{changeError}</p>}
          {changeSuccess && <p className="text-xs text-emerald-600">{changeSuccess}</p>}

          <button
            type="submit"
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-300"
            disabled={changeBusy}
          >
            {changeBusy ? "กำลังเปลี่ยนรหัสผ่าน…" : "เปลี่ยนรหัสผ่าน"}
          </button>
        </form>
        <p className="mt-3 text-xs text-slate-500">
          หมายเหตุ: หากกรอกรหัสผ่านเดิมผิดเกิน 10 ครั้ง บัญชีจะถูกพักการใช้งานโดยอัตโนมัติ และต้องให้ผู้บังคับบัญชารีเซ็ตรหัสผ่านใหม่ให้
        </p>
      </section>
    </div>
  );
};

export default ProfilePage;
