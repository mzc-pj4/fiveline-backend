import { Navigate, Route, Routes } from "react-router-dom";
import { getAdminUser, isAdminAuthenticated } from "./auth";
import AdminDashboard from "./pages/AdminDashboard";
import AdminLogin from "./pages/AdminLogin";
import AdminRegister from "./pages/AdminRegister";

function RequireAdmin({ children }: { children: JSX.Element }) {
  const user = getAdminUser();
  if (!isAdminAuthenticated() || user?.role !== "admin") return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AdminLogin />} />
      <Route path="/register" element={<AdminRegister />} />
      <Route path="/*" element={<RequireAdmin><AdminDashboard /></RequireAdmin>} />
    </Routes>
  );
}
