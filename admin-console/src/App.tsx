import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Layout } from "./components/Layout";
import { AdminRoute } from "./components/AdminRoute";
import { DepartmentRoute } from "./components/DepartmentRoute";
import { LoginPage } from "./pages/LoginPage";
import ThaiDCallbackPage from "./pages/ThaiDCallbackPage";
import OfficersListPage from "./pages/OfficersListPage";
import OfficerCreatePage from "./pages/OfficerCreatePage";
import OfficerDetailPage from "./pages/OfficerDetailPage";
import ProfilePage from "./pages/ProfilePage";
import ClientAccessPage from "./pages/ClientAccessPage";
import CommunityQuickSearchPage from "./pages/CommunityQuickSearchPage";
import OfficerRegisterPage from "./pages/OfficerRegisterPage";

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<OfficerRegisterPage />} />
    <Route path="/thaid/callback" element={<ThaiDCallbackPage />} />
        <Route
          path="/officers"
          element={
            <ProtectedRoute>
              <Layout>
                <OfficersListPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/officers/create"
          element={
            <ProtectedRoute>
              <Layout>
                <OfficerCreatePage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/officers/:officerId"
          element={
            <ProtectedRoute>
              <Layout>
                <OfficerDetailPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Layout>
                <ProfilePage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/access-control"
          element={
            <ProtectedRoute>
              <AdminRoute>
                <Layout>
                  <ClientAccessPage />
                </Layout>
              </AdminRoute>
            </ProtectedRoute>
          }
        />
        <Route
          path="/search/community"
          element={
            <ProtectedRoute>
              <DepartmentRoute>
                <Layout>
                  <CommunityQuickSearchPage />
                </Layout>
              </DepartmentRoute>
            </ProtectedRoute>
          }
        />
        <Route path="/search/osm" element={<Navigate to="/search/community" replace />} />
        <Route path="/search/yuwa-osm" element={<Navigate to="/search/community" replace />} />
        <Route path="/" element={<Navigate to="/officers" replace />} />
        <Route path="*" element={<Navigate to="/officers" replace />} />
      </Routes>
    </AuthProvider>
  );
};

export default App;