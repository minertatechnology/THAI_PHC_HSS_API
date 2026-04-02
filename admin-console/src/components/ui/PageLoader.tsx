import React from "react";

type PageLoaderProps = {
  message?: string;
  minHeight?: number;
};

export const PageLoader: React.FC<PageLoaderProps> = ({ message = "กำลังโหลดข้อมูล…", minHeight = 320 }: PageLoaderProps) => (
  <div
    className="flex w-full items-center justify-center rounded-2xl border border-slate-200 bg-white p-12 shadow-sm"
    style={{ minHeight }}
  >
    <div className="flex flex-col items-center gap-4 text-slate-500">
      <span className="relative inline-flex h-14 w-14 items-center justify-center">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-200/60" />
        <span className="relative inline-flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 via-blue-500 to-sky-500 text-white shadow-lg">
          <svg className="h-6 w-6 animate-spin text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v4m0 8v4m8-8h-4M8 12H4m11.314 6.314-2.828-2.828m0-5.657 2.828-2.829M8.686 17.657l2.828-2.828M11.514 9.172 8.686 6.343" />
          </svg>
        </span>
      </span>
      <p className="text-sm font-medium text-slate-600">{message}</p>
    </div>
  </div>
);

export default PageLoader;
