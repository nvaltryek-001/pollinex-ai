import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
import { useAuth } from "./lib/auth";
import type { Role } from "./lib/types";
import Landing from "./pages/Landing";
import AuthPage from "./pages/AuthPage";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Scanner = lazy(() => import("./pages/Scanner"));
const ScanDetail = lazy(() => import("./pages/ScanDetail"));
const SpeciesPage = lazy(() => import("./pages/SpeciesPage"));
const StructurePage = lazy(() => import("./pages/ModulePages").then((m) => ({ default: m.StructurePage })));
const MaturityPage = lazy(() => import("./pages/ModulePages").then((m) => ({ default: m.MaturityPage })));
const HealthPage = lazy(() => import("./pages/ModulePages").then((m) => ({ default: m.HealthPage })));
const ReadinessPage = lazy(() => import("./pages/ReadinessPage"));
const Simulator = lazy(() => import("./pages/Simulator"));
const EnvironmentPage = lazy(() => import("./pages/EnvironmentPage"));
const FieldsPage = lazy(() => import("./pages/FieldsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const EvaluationPage = lazy(() => import("./pages/EvaluationPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const ResearchPage = lazy(() => import("./pages/ResearchPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const DatasetsPage = lazy(() => import("./pages/DatasetsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

function Protected({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { user, loading, hasRole } = useAuth();
  const loc = useLocation();
  if (loading) return <div className="p-8"><Loading text="Checking session" /></div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (roles && !hasRole(...roles)) return <div className="p-8 text-sm text-muted">You do not have permission to view this page.</div>;
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<div className="p-8"><Loading /></div>}>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/app" element={<Protected><Layout /></Protected>}>
          <Route index element={<Dashboard />} />
          <Route path="scanner" element={<Scanner />} />
          <Route path="scans/:id" element={<ScanDetail />} />
          <Route path="species" element={<SpeciesPage />} />
          <Route path="structure" element={<StructurePage />} />
          <Route path="maturity" element={<MaturityPage />} />
          <Route path="readiness" element={<ReadinessPage />} />
          <Route path="health" element={<HealthPage />} />
          <Route path="simulator" element={<Simulator />} />
          <Route path="environment" element={<EnvironmentPage />} />
          <Route path="fields" element={<FieldsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="evaluation" element={<EvaluationPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="research" element={<ResearchPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="datasets" element={<DatasetsPage />} />
          <Route path="admin" element={<Protected roles={["admin"]}><AdminPage /></Protected>} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
