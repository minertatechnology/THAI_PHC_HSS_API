import React, { useEffect, useRef, useState } from "react";
import PasswordInput from "./PasswordInput";
import { changePassword } from "../api/auth";
import { useAuth } from "../hooks/useAuth";

const ForcedPasswordChangeDialog: React.FC = () => {
  const { logout, refreshProfile, completePasswordChange } = useAuth();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const closeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (closeTimerRef.current !== null) {
        window.clearTimeout(closeTimerRef.current);
      }
    };
  }, []);

  const handleFieldChange = (field: "current" | "next" | "confirm") => (event: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const resolveErrorMessage = (detail: unknown): string => {
    if (typeof detail !== "string") {
      return "ไม่สามารถเปลี่ยนรหัสผ่านได้ กรุณาลองใหม่";
    }
    if (detail === "old_password_incorrect") {
      return "รหัสผ่านชั่วคราวไม่ถูกต้อง กรุณาลองอีกครั้ง";
    }
    if (detail === "password_unchanged") {
      return "รหัสผ่านใหม่ต้องแตกต่างจากรหัสผ่านเดิม";
    }
    if (detail === "account_locked") {
      return "คุณใส่รหัสผ่านชั่วคราวผิดเกินกำหนด บัญชีถูกพักใช้งาน กรุณาติดต่อผู้ดูแลระบบ";
    }
    if (detail === "password_not_set") {
      return "บัญชีนี้ยังไม่ได้ตั้งรหัสผ่าน กรุณาติดต่อผู้ดูแลระบบ";
    }
    return "ไม่สามารถเปลี่ยนรหัสผ่านได้ กรุณาลองใหม่";
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) {
      return;
    }
    setError(null);

    if (!form.current || !form.next) {
      setError("กรุณากรอกรหัสผ่านชั่วคราวและรหัสผ่านใหม่ให้ครบถ้วน");
      return;
    }
    if (form.next !== form.confirm) {
      setError("รหัสผ่านใหม่และยืนยันรหัสผ่านไม่ตรงกัน");
      return;
    }
    if (form.next.length < 8) {
      setError("รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 8 ตัวอักษร");
      return;
    }

    setSubmitting(true);
    try {
      await changePassword({ old_password: form.current, new_password: form.next });
      await refreshProfile();
      setSuccess(true);
      closeTimerRef.current = window.setTimeout(() => {
        completePasswordChange();
      }, 1200);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(resolveErrorMessage(detail));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  const isDisabled = submitting || success;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 px-4">
      <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
        <div className="space-y-2 text-center">
          <h2 className="text-xl font-semibold text-slate-900">จำเป็นต้องเปลี่ยนรหัสผ่าน</h2>
          <p className="text-sm text-slate-600">
            ระบบตรวจพบว่าคุณเข้าสู่ระบบด้วยรหัสผ่านชั่วคราว กรุณาเปลี่ยนรหัสผ่านก่อนใช้งานต่อ
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="current-password">
              รหัสผ่านชั่วคราว
            </label>
            <PasswordInput
              id="current-password"
              value={form.current}
              onChange={handleFieldChange("current")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              autoComplete="current-password"
              disabled={isDisabled}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="new-password">
              รหัสผ่านใหม่
            </label>
            <PasswordInput
              id="new-password"
              value={form.next}
              onChange={handleFieldChange("next")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              autoComplete="new-password"
              disabled={isDisabled}
              required
            />
            <p className="mt-1 text-xs text-slate-500">ต้องมีความยาวอย่างน้อย 8 ตัวอักษร และควรผสมตัวเลขหรือสัญลักษณ์เพื่อความปลอดภัย</p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="confirm-password">
              ยืนยันรหัสผ่านใหม่
            </label>
            <PasswordInput
              id="confirm-password"
              value={form.confirm}
              onChange={handleFieldChange("confirm")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              autoComplete="new-password"
              disabled={isDisabled}
              required
            />
          </div>

          {error && <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">{error}</div>}
          {success && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-600">
              เปลี่ยนรหัสผ่านสำเร็จ ระบบจะปิดกล่องนี้ให้อัตโนมัติ
            </div>
          )}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="submit"
              className="inline-flex w-full items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto"
              disabled={isDisabled}
            >
              {submitting ? "กำลังบันทึก…" : "เปลี่ยนรหัสผ่าน"}
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex w-full items-center justify-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-400 hover:bg-slate-100 sm:w-auto"
              disabled={submitting}
            >
              ออกจากระบบ
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ForcedPasswordChangeDialog;
