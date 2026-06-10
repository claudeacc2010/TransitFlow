// Роутинг по роли. Неавторизованный → /login; дальше кабинет по роли.
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth";
import Analyst from "./pages/Analyst";
import Carrier from "./pages/Carrier";
import Login from "./pages/Login";
import Shipper from "./pages/Shipper";

const HOME_BY_ROLE = {
  shipper: "/shipper",
  carrier: "/carrier",
  analyst: "/analyst",
};

function RequireRole({ role, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={HOME_BY_ROLE[user.role] || "/login"} replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="empty" style={{ paddingTop: 80 }}>Загрузка…</div>;
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to={HOME_BY_ROLE[user.role]} replace /> : <Login />}
      />
      <Route
        path="/shipper"
        element={
          <RequireRole role="shipper">
            <Shipper />
          </RequireRole>
        }
      />
      <Route
        path="/carrier"
        element={
          <RequireRole role="carrier">
            <Carrier />
          </RequireRole>
        }
      />
      <Route
        path="/analyst"
        element={
          <RequireRole role="analyst">
            <Analyst />
          </RequireRole>
        }
      />
      <Route
        path="*"
        element={<Navigate to={user ? HOME_BY_ROLE[user.role] : "/login"} replace />}
      />
    </Routes>
  );
}
