import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createOfficer } from "../api/officers";
import { OfficerCreatePayload } from "../types/officer";
import { OfficerForm } from "../components/OfficerForm";

const resolveCreateOfficerErrorMessage = (err: unknown): string => {
  const detail = (err as { response?: { data?: { detail?: unknown } } })
    ?.response?.data?.detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = Array.isArray(first?.loc)
      ? first.loc.filter((item) => typeof item === "string").join(".")
      : "";
    const msg = first?.msg ?? "ข้อมูลไม่ถูกต้อง";
    return field ? `ไม่สามารถสร้างบัญชีได้: ${field} - ${msg}` : `ไม่สามารถสร้างบัญชีได้: ${msg}`;
  }
  if (typeof detail === "string" && detail.trim()) {
    return `ไม่สามารถสร้างบัญชีได้: ${detail}`;
  }
  return "ไม่สามารถสร้างบัญชีเจ้าหน้าที่ได้ กรุณาตรวจสอบข้อมูลและลองใหม่อีกครั้ง";
};

const OfficerCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: OfficerCreatePayload) => {
    setSubmitting(true);
    setError(null);
    try {
      const officer = await createOfficer(values);
      navigate(`/officers/${officer.id}`);
    } catch (err) {
      setError(resolveCreateOfficerErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-3 rounded-2xl bg-gradient-to-r from-blue-600 via-blue-500 to-sky-500 p-6 text-white shadow-lg">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-white/80">Create new officer</p>
          <h1 className="text-2xl font-bold">เพิ่มเจ้าหน้าที่ใหม่</h1>
          <p className="text-sm text-white/80">กรอกข้อมูลเพื่อสร้างบัญชีสำหรับเจ้าหน้าที่</p>
        </div>
      </header>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {error && (
          <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-inner">
            {error}
          </div>
        )}
        <OfficerForm
          mode="create"
          onSubmit={(values) => handleSubmit(values as OfficerCreatePayload)}
          isSubmitting={submitting}
        />
      </section>
    </div>
  );
};

export default OfficerCreatePage;