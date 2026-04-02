import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { canUseDepartmentLookups } from "../utils/permissions";
import { PageLoader } from "./ui/PageLoader";

interface DepartmentRouteProps {
  children: React.ReactNode;
}

export const DepartmentRoute: React.FC<DepartmentRouteProps> = ({ children }: DepartmentRouteProps) => {
  const { user, isLoading } = useAuth();
  const authorized = canUseDepartmentLookups(user);

  if (isLoading) {
    return (
      <div className="p-6">
        <PageLoader message="กำลังตรวจสอบสิทธิ์ระดับกรม" minHeight={240} />
      </div>
    );
  }

  if (!authorized) {
    return <Navigate to="/officers" replace />;
  }

  return <>{children}</>;
};

export default DepartmentRoute;
