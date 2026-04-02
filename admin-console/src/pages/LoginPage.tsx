import React, { ChangeEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageLoader } from "../components/ui/PageLoader";
import PasswordInput from "../components/PasswordInput";

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate("/officers", { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4 py-12">
        <div className="mx-auto w-full max-w-md">
          <PageLoader message="กำลังโหลดข้อมูลการเข้าสู่ระบบ" minHeight={280} />
        </div>
      </div>
    );
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate("/officers", { replace: true });
    } catch (err) {
      setError("Login failed. Please verify citizen ID and password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4 py-12">
      <div className="mx-auto flex w-full max-w-md flex-col items-center justify-center gap-8">
        <div className="inline-flex items-center gap-3 rounded-full bg-white/80 px-5 py-2 shadow-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-lg font-bold text-white">
            PHC
          </span>
          <div className="flex flex-col">
            <span className="text-xs font-semibold uppercase tracking-wide text-blue-700">Thai HSS</span>
            <span className="text-sm font-medium text-slate-700">Officer Admin Console</span>
          </div>
        </div>

        <div className="w-full rounded-2xl border border-white/70 bg-white/90 p-8 shadow-xl backdrop-blur">
          <div className="mb-6 space-y-2 text-center">
            <h1 className="text-2xl font-semibold text-slate-900">เข้าสู่ระบบ</h1>
            <p className="text-sm text-slate-500">ใช้ข้อมูลประจำตัวเจ้าหน้าที่ที่ลงทะเบียนไว้</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="username" className="text-sm font-medium text-slate-700">
                เลขประจำตัวประชาชน
              </label>
              <input
                id="username"
                value={username}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setUsername(event.target.value)}
                autoComplete="username"
                placeholder="เลขประจำตัวประชาชน"
                required
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-slate-700">
                รหัสผ่าน
              </label>
              <PasswordInput
                id="password"
                value={password}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setPassword(event.target.value)}
                autoComplete="current-password"
                placeholder="รหัสผ่าน"
                required
                className="h-11 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 shadow-sm transition focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              />
            </div>

            {error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !username || !password}
              className="inline-flex w-full items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {submitting ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบ"}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white/90 px-3 text-slate-400">หรือ</span>
            </div>
          </div>

          {/* ThaiD Login Button */}
          <button
            type="button"
            onClick={() => {
              const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "");
              const clientId = import.meta.env.VITE_OAUTH_CLIENT_ID ?? "";
              const callbackUrl = `${window.location.origin}/thaid/callback`;
              const params = new URLSearchParams({
                client_id: clientId,
                user_type: "officer",
                redirect_uri: callbackUrl,
              });
              window.location.href = `${apiBase}/thaid/authorize?${params}`;
            }}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 hover:border-slate-300"
          >
            <img src="/thaiid-logo.png" alt="ThaiD" className="h-6" />
            เข้าสู่ระบบด้วย ThaiD
          </button>
        </div>

        <div className="text-center text-xs text-slate-500">
          <p>เข้าถึงได้เฉพาะเจ้าหน้าที่สาธารณสุขที่ได้รับอนุญาตเท่านั้น</p>
          <p className="mt-3">
            ยังไม่มีบัญชี? {" "}
            <Link to="/register" className="font-semibold text-blue-600 transition hover:text-blue-700">
              ลงทะเบียนเจ้าหน้าที่
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};