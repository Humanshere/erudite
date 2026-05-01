import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="page">Loading...</div>;
  }

  if (!user) {
    return <Navigate to={`/login${location.search}`} replace />;
  }

  return children;
}
