import { useState } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
    } catch {
      setError("Invalid credentials. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      {/* Left panel */}
      <div className="login-left">
        <div className="login-brand">
          <div className="login-logo">
            <div className="login-logo-icon">🎓</div>
            <h2>University<br />Management System</h2>
          </div>
          <h1 className="login-headline">
            Manage your<br />
            institution with<br />
            <span>clarity.</span>
          </h1>
          <p className="login-tagline">
            Centralized operations for admins, faculty, and students — attendance, enrollment, and more.
          </p>
        </div>

        <div className="login-features">
          <div className="login-feature">
            <div className="login-feature-icon">👤</div>
            <span>Role-based access for Admin, Faculty &amp; Student</span>
          </div>
          <div className="login-feature">
            <div className="login-feature-icon">📋</div>
            <span>Mark and track attendance by course and date</span>
          </div>
          <div className="login-feature">
            <div className="login-feature-icon">📊</div>
            <span>Course-wise insights and enrollment overview</span>
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div className="login-right">
        <div className="login-form-card">
          <h1>Welcome back</h1>
          <p>Sign in with your role account credentials.</p>

          <form onSubmit={onSubmit} className="login-form-inner">
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                placeholder="you@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <div className="error">{error}</div>}
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "Signing in…" : "Sign in →"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
