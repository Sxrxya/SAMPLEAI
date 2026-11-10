import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

const AuthPage = lazy(() =>
  import("./pages/AuthPage").then((module) => ({ default: module.AuthPage })),
);
const LandingPage = lazy(() =>
  import("./pages/LandingPage").then((module) => ({
    default: module.LandingPage,
  })),
);
const PortalPage = lazy(() =>
  import("./pages/PortalPage").then((module) => ({
    default: module.PortalPage,
  })),
);
const PortalLayout = lazy(() =>
  import("./components/PortalLayout").then((module) => ({
    default: module.PortalLayout,
  })),
);
const ProtectedRoute = lazy(() =>
  import("./routes/ProtectedRoute").then((module) => ({
    default: module.ProtectedRoute,
  })),
);

export default function App() {
  return (
    <BrowserRouter>
      <Suspense
        fallback={
          <div className="route-loading" role="status">
            Opening your workspace…
          </div>
        }
      >
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login/:role" element={<AuthPage />} />
          <Route
            path="/portal/:role/:section"
            element={
              <ProtectedRoute>
                <PortalLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<PortalPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
