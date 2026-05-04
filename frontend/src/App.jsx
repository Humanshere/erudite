import { Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";

import ProtectedRoute from "./components/ProtectedRoute";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import ChatWidget from "./components/ChatWidget/ChatWidget";
import "./styles.css";

export default function App() {
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if (e.altKey && (e.key === "c" || e.key === "C")) {
        setChatOpen((s) => !s);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <>
      <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <ChatWidget open={chatOpen} onClose={() => setChatOpen(false)} />
    </>
  );
}
