import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { canManageClientAccess } from "../utils/permissions";
import { PageLoader } from "./ui/PageLoader";

interface AdminRouteProps {
  children: React.ReactNode;
}

export const AdminRoute: React.FC<AdminRouteProps> = ({ children }: AdminRouteProps) => {
  const { user, isLoading } = useAuth();
  const hasPermission = canManageClientAccess(user);

  if (isLoading) {
    return (
      <div className="p-6">
        <PageLoader message="กำลังตรวจสอบสิทธิ์ผู้ดูแล" minHeight={240} />
      </div>
    );
  }

  if (!hasPermission) {
    return <Navigate to="/officers" replace />;
  }

  return <>{children}</>;
};
