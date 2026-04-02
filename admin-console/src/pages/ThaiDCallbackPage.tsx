import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageLoader } from "../components/ui/PageLoader";

/**
 * ThaiD DOPA callback landing page.
 *
 * After the user authenticates via ThaiD, DOPA redirects to the API server's
 * `/callback` endpoint which exchanges the code and then redirects here:
 *
 *   /thaid/callback?access_token=...&refresh_token=...&expires_in=...&user_type=...&user_id=...
 *
 * This page reads the tokens from query parameters, saves them into the auth
 * context, and redirects the user to the main app.
 */
const ThaiDCallbackPage: React.FC = () => {
  const { loginWithTokens, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    const params = new URLSearchParams(window.location.search);

    // --- Error from API callback ---
    const errorParam = params.get("error");
    if (errorParam) {
      const messages: Record<string, string> = {
        thaid_not_configured: "ระบบ ThaiD ยังไม่ได้ตั้งค่า กรุณาติดต่อผู้ดูแลระบบ",
        missing_client_id: "ไม่พบ client_id กรุณาลองใหม่อีกครั้ง",
        citizen_id_not_found: "ไม่พบบัญชีผู้ใช้ในระบบ กรุณาลงทะเบียนก่อนใช้งาน",
        user_not_found: "ไม่พบบัญชีผู้ใช้ในระบบ กรุณาลงทะเบียนก่อนใช้งาน",
        user_type_not_allowed: "ประเภทผู้ใช้ไม่ได้รับอนุญาตสำหรับระบบนี้",
        user_blocked: "บัญชีของคุณถูกบล็อก กรุณาติดต่อผู้ดูแลระบบ",
        user_not_in_allowlist: "บัญชีไม่อยู่ในรายการที่อนุญาต กรุณาติดต่อผู้ดูแลระบบ",
        inactive_account: "บัญชีถูกปิดใช้งาน กรุณาติดต่อผู้ดูแลระบบ",
        invalid_auth_code: "รหัสยืนยันตัวตนไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง",
        thaid_token_exchange_failed: "ไม่สามารถเชื่อมต่อกับระบบ ThaiD ได้ กรุณาลองใหม่อีกครั้ง",
        thaid_network_error: "ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ ThaiD ได้ กรุณาลองใหม่",
        thaid_missing_pid: "ไม่พบเลขประจำตัวประชาชนจากการยืนยัน ThaiD",
        invalid_client: "client ไม่ถูกต้อง กรุณาติดต่อผู้ดูแลระบบ",
        invalid_scope: "ขอบเขตสิทธิ์ไม่ถูกต้อง กรุณาติดต่อผู้ดูแลระบบ",
        state_tampered: "ข้อมูลความปลอดภัยไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง",
        invalid_state: "ข้อมูล state ไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง",
        internal_error: "เกิดข้อผิดพลาดภายในระบบ กรุณาลองใหม่อีกครั้ง",
      };
      setError(messages[errorParam] ?? `เข้าสู่ระบบไม่สำเร็จ: ${errorParam}`);
      return;
    }

    // --- Extract tokens ---
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token") || null;
    const expiresIn = Number(params.get("expires_in") || "3600");

    if (!accessToken) {
      setError("ไม่พบ access token จากการยืนยันตัวตน ThaiD");
      return;
    }

    // Save tokens into auth context and navigate to main page
    loginWithTokens(accessToken, refreshToken, expiresIn)
      .then(() => {
        navigate("/officers", { replace: true });
      })
      .catch(() => {
        setError("ไม่สามารถเข้าสู่ระบบได้ กรุณาลองใหม่อีกครั้ง");
      });
  }, [loginWithTokens, navigate]);

  // If already authenticated, redirect
  useEffect(() => {
    if (isAuthenticated && !error) {
      navigate("/officers", { replace: true });
    }
  }, [isAuthenticated, error, navigate]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4">
        <div className="w-full max-w-md rounded-2xl border border-white/70 bg-white/90 p-8 shadow-xl backdrop-blur">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-rose-100 mx-auto">
            <svg className="h-7 w-7 text-rose-500" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
          </div>
          <h2 className="text-center text-lg font-semibold text-slate-900 mb-2">
            เข้าสู่ระบบด้วย ThaiD ไม่สำเร็จ
          </h2>
          <p className="text-center text-sm text-slate-600 mb-6">{error}</p>
          <button
            onClick={() => navigate("/login", { replace: true })}
            className="inline-flex w-full items-center justify-center rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-700"
          >
            กลับหน้าเข้าสู่ระบบ
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-blue-100 px-4 py-12">
      <div className="mx-auto w-full max-w-md">
        <PageLoader message="กำลังเข้าสู่ระบบด้วย ThaiD..." minHeight={280} />
      </div>
    </div>
  );
};

export default ThaiDCallbackPage;
