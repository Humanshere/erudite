import { useEffect, useMemo, useState } from "react";

import client from "../api/client";
import { useAuth } from "../auth/AuthContext";

/* ─── SIDEBAR SHELL ─────────────────────────────────────────────── */

function AppShell({ children, user, logout, activeNav, setActiveNav }) {
  const todayText = useMemo(() => {
    return new Date().toLocaleDateString(undefined, {
      weekday: "short", month: "short", day: "numeric", year: "numeric",
    });
  }, []);

  const navItems = useMemo(() => {
    if (user.role === "admin") {
      return [
        { id: "users",       label: "Users",           icon: "👤" },
        { id: "courses",     label: "Courses",         icon: "📚" },
        { id: "enrollments", label: "Enrollments",     icon: "📋" },
      ];
    }
    if (user.role === "faculty") {
      return [
        { id: "timetable",   label: "Timetable",       icon: "🗓️" },
      ];
    }
    return [
      { id: "overview",    label: "Overview",          icon: "📊" },
      { id: "history",     label: "Attendance Log",    icon: "🗂️" },
    ];
  }, [user.role]);

  const panelTitle = useMemo(() => {
    const map = {
      users: "User Management",
      courses: "Course Allocation",
      enrollments: "Enrollment Management",
      attendance: "Mark Attendance",
      timetable: "Class Timetable",
      overview: "My Attendance",
      history: "Attendance Log",
    };
    return map[activeNav] || "Dashboard";
  }, [activeNav]);

  const panelSub = useMemo(() => {
    const map = {
      users: "Create accounts and manage all users",
      courses: "Assign faculty and create new courses",
      enrollments: "Enroll students and manage course rosters",
      attendance: "Mark and save attendance by course and date",
      timetable: "Auto schedule recurring classes and add extra sessions",
      overview: "Your attendance summary across all courses",
      history: "Full record of your past attendance",
    };
    return map[activeNav] || "";
  }, [activeNav]);

  const initials = user.full_name
    ? user.full_name.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase()
    : "U";

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-mark">
            <div className="logo-icon">🎓</div>
            <h2>Erudite</h2>
          </div>
          <p>Management System</p>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-user-info">
            <div className="user-avatar">{initials}</div>
            <div>
              <div className="sidebar-user-name">{user.full_name}</div>
              <div className="sidebar-user-role">{user.role}</div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="sidebar-section-label">Navigation</div>
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`sidebar-nav-item ${activeNav === item.id ? "active" : ""}`}
              onClick={() => setActiveNav(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button type="button" onClick={logout}>
            <span>⎋</span> Sign Out
          </button>
        </div>
      </aside>

      {/* Main area */}
      <main className="main-area">
        <div className="topbar">
          <div className="topbar-title">
            <h1>{panelTitle}</h1>
            {panelSub && <p>{panelSub}</p>}
          </div>
          <div className="topbar-right">
            <span className="date-chip">📅 {todayText}</span>
          </div>
        </div>

        <div className="content-area">
          {children}
        </div>
      </main>
    </div>
  );
}

/* ─── ADMIN PANEL ───────────────────────────────────────────────── */

function AdminPanel({ activeSection }) {
  const [loading, setLoading] = useState(true);
  const [userQuery, setUserQuery] = useState("");
  const [courseQuery, setCourseQuery] = useState("");
  const [courses, setCourses] = useState([]);
  const [facultyUsers, setFacultyUsers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [students, setStudents] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [assignments, setAssignments] = useState({});
  const [newEnrollment, setNewEnrollment] = useState({ student: "", course: "" });
  const [newCourse, setNewCourse] = useState({
    code: "", title: "", credits: 3, department: "", semester: "", faculty: "",
  });
  const [newUser, setNewUser] = useState({
    full_name: "", email: "", role: "student", password: "",
  });
  const [message, setMessage] = useState({ text: "", type: "info" });

  const notify = (text, type = "info") => setMessage({ text, type });

  const loadData = async () => {
    setMessage({ text: "", type: "info" });
    setLoading(true);
    const [courseRes, facultyRes, studentRes, enrollmentRes, departmentRes, semesterRes, usersRes] =
      await Promise.all([
        client.get("/academics/courses/"),
        client.get("/auth/users/?role=faculty"),
        client.get("/auth/users/?role=student"),
        client.get("/academics/enrollments/"),
        client.get("/academics/departments/"),
        client.get("/academics/semesters/"),
        client.get("/auth/users/"),
      ]);

    setCourses(courseRes.data);
    setFacultyUsers(facultyRes.data);
    setStudents(studentRes.data);
    setEnrollments(enrollmentRes.data);
    setDepartments(departmentRes.data);
    setSemesters(semesterRes.data);
    setAllUsers(usersRes.data);

    const map = {};
    courseRes.data.forEach((c) => { map[c.id] = c.faculty ?? ""; });
    setAssignments(map);

    if (studentRes.data.length > 0 && !newEnrollment.student)
      setNewEnrollment((p) => ({ ...p, student: String(studentRes.data[0].id) }));
    if (courseRes.data.length > 0 && !newEnrollment.course)
      setNewEnrollment((p) => ({ ...p, course: String(courseRes.data[0].id) }));
    if (departmentRes.data.length > 0 && !newCourse.department)
      setNewCourse((p) => ({ ...p, department: String(departmentRes.data[0].id) }));
    if (semesterRes.data.length > 0 && !newCourse.semester)
      setNewCourse((p) => ({ ...p, semester: String(semesterRes.data[0].id) }));

    setLoading(false);
  };

  useEffect(() => { loadData(); }, []);

  const onFacultyChange = (courseId, facultyId) =>
    setAssignments((p) => ({ ...p, [courseId]: facultyId ? Number(facultyId) : "" }));

  const saveAllocation = async (courseId) => {
    await client.patch(`/academics/courses/${courseId}/`, { faculty: assignments[courseId] || null });
    notify("Faculty allocation saved.", "success");
    await loadData();
  };

  const createEnrollment = async () => {
    if (!newEnrollment.student || !newEnrollment.course) { notify("Select a student and course.", "warning"); return; }
    try {
      await client.post("/academics/enrollments/", {
        student: Number(newEnrollment.student),
        course: Number(newEnrollment.course),
      });
      notify("Enrollment created successfully.", "success");
      await loadData();
    } catch (err) {
      notify(err?.response?.data?.non_field_errors?.[0] || "Could not create enrollment.");
    }
  };

  const deleteEnrollment = async (id) => {
    await client.delete(`/academics/enrollments/${id}/`);
    notify("Enrollment removed.", "success");
    await loadData();
  };

  const createCourse = async () => {
    if (!newCourse.code || !newCourse.title || !newCourse.department || !newCourse.semester) {
      notify("Code, title, department, and semester are required.", "warning"); return;
    }
    try {
      await client.post("/academics/courses/", {
        code: newCourse.code.trim(),
        title: newCourse.title.trim(),
        credits: Number(newCourse.credits) || 0,
        department: Number(newCourse.department),
        semester: Number(newCourse.semester),
        faculty: newCourse.faculty ? Number(newCourse.faculty) : null,
      });
      notify("Course created successfully.", "success");
      setNewCourse((p) => ({ ...p, code: "", title: "", credits: 3, faculty: "" }));
      await loadData();
    } catch (err) {
      notify(err?.response?.data?.code?.[0] || "Could not create course.");
    }
  };

  const createUser = async () => {
    if (!newUser.full_name || !newUser.email || !newUser.role || !newUser.password) {
      notify("All fields are required.", "warning"); return;
    }
    try {
      await client.post("/auth/register/", {
        full_name: newUser.full_name.trim(),
        email: newUser.email.trim().toLowerCase(),
        role: newUser.role,
        password: newUser.password,
      });
      notify("User created successfully.", "success");
      setNewUser({ full_name: "", email: "", role: "student", password: "" });
      await loadData();
    } catch (err) {
      const d = err?.response?.data;
      notify(d?.email?.[0] || d?.password?.[0] || "Could not create user.");
    }
  };

  const filteredUsers = allUsers.filter((u) => {
    const q = userQuery.trim().toLowerCase();
    return !q || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q) || u.role.toLowerCase().includes(q);
  });

  const filteredCourses = courses.filter((c) => {
    const q = courseQuery.trim().toLowerCase();
    return !q || c.code.toLowerCase().includes(q) || c.title.toLowerCase().includes(q) || (c.faculty_name || "").toLowerCase().includes(q);
  });

  const alertClass = { info: "alert alert-info", success: "alert alert-success", warning: "alert alert-warning" };

  if (loading) return <div className="alert alert-info">Loading data…</div>;

  return (
    <div className="grid-gap">
      {/* Stats */}
      <div className="stat-grid">
        <div className="stat-card blue">
          <span className="stat-icon">👥</span>
          <span className="stat-label">Total Users</span>
          <strong className="stat-value">{allUsers.length}</strong>
        </div>
        <div className="stat-card teal">
          <span className="stat-icon">📚</span>
          <span className="stat-label">Courses</span>
          <strong className="stat-value">{courses.length}</strong>
        </div>
        <div className="stat-card green">
          <span className="stat-icon">🧑‍🏫</span>
          <span className="stat-label">Faculty</span>
          <strong className="stat-value">{facultyUsers.length}</strong>
        </div>
        <div className="stat-card amber">
          <span className="stat-icon">📋</span>
          <span className="stat-label">Enrollments</span>
          <strong className="stat-value">{enrollments.length}</strong>
        </div>
      </div>

      {/* Content by section */}
      {activeSection === "users" && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Create New User</h3>
              <p>Add a student, faculty member, or admin account</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="form-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
              <div className="form-group">
                <label>Full Name</label>
                <input type="text" placeholder="Jane Doe" value={newUser.full_name}
                  onChange={(e) => setNewUser((p) => ({ ...p, full_name: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input type="email" placeholder="jane@univ.edu" value={newUser.email}
                  onChange={(e) => setNewUser((p) => ({ ...p, email: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select value={newUser.role} onChange={(e) => setNewUser((p) => ({ ...p, role: e.target.value }))}>
                  <option value="student">Student</option>
                  <option value="faculty">Faculty</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group">
                <label>Temporary Password</label>
                <input type="password" placeholder="••••••••" value={newUser.password}
                  onChange={(e) => setNewUser((p) => ({ ...p, password: e.target.value }))} />
              </div>
              <div className="form-group" style={{ justifyContent: "flex-end" }}>
                <label>&nbsp;</label>
                <button type="button" className="btn-primary" onClick={createUser}>
                  + Create User
                </button>
              </div>
            </div>
          </div>

          <div className="panel-header" style={{ borderTop: "1px solid var(--border)" }}>
            <h3>All Users</h3>
            <div className="search-bar" style={{ width: 260 }}>
              <span className="search-icon">🔍</span>
              <input type="text" placeholder="Search name, email, role…"
                value={userQuery} onChange={(e) => setUserQuery(e.target.value)} />
            </div>
          </div>
          <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr key={u.id}>
                    <td><strong>{u.full_name}</strong></td>
                    <td className="td-muted">{u.email}</td>
                    <td>
                      <span className={`badge badge-role`} style={{ textTransform: "capitalize" }}>{u.role}</span>
                    </td>
                    <td>
                      <span className={`status-dot ${u.is_active ? "active" : "inactive"}`}>
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
                {filteredUsers.length === 0 && (
                  <tr><td colSpan={4} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No users match your search.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {message.text && <div className="panel-body"><div className={alertClass[message.type] || "alert alert-info"}>{message.text}</div></div>}
        </div>
      )}

      {activeSection === "courses" && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Create New Course</h3>
              <p>Define course details, department, and optional faculty assignment</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="form-grid">
              <div className="form-group">
                <label>Course Code</label>
                <input type="text" placeholder="e.g. CSE102" value={newCourse.code}
                  onChange={(e) => setNewCourse((p) => ({ ...p, code: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Course Title</label>
                <input type="text" placeholder="Data Structures" value={newCourse.title}
                  onChange={(e) => setNewCourse((p) => ({ ...p, title: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Credits</label>
                <input type="number" min="1" value={newCourse.credits}
                  onChange={(e) => setNewCourse((p) => ({ ...p, credits: e.target.value }))} />
              </div>
              <div className="form-group">
                <label>Department</label>
                <select value={newCourse.department} onChange={(e) => setNewCourse((p) => ({ ...p, department: e.target.value }))}>
                  <option value="">Select Department</option>
                  {departments.map((d) => <option key={d.id} value={d.id}>{d.code} – {d.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Semester</label>
                <select value={newCourse.semester} onChange={(e) => setNewCourse((p) => ({ ...p, semester: e.target.value }))}>
                  <option value="">Select Semester</option>
                  {semesters.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Faculty (optional)</label>
                <select value={newCourse.faculty} onChange={(e) => setNewCourse((p) => ({ ...p, faculty: e.target.value }))}>
                  <option value="">Unassigned</option>
                  {facultyUsers.map((f) => <option key={f.id} value={f.id}>{f.full_name}</option>)}
                </select>
              </div>
            </div>
            <div style={{ marginTop: 16 }}>
              <button type="button" className="btn-primary" onClick={createCourse}>+ Create Course</button>
            </div>
          </div>

          <div className="panel-header" style={{ borderTop: "1px solid var(--border)" }}>
            <h3>All Courses</h3>
            <div className="search-bar" style={{ width: 280 }}>
              <span className="search-icon">🔍</span>
              <input type="text" placeholder="Search code, title, faculty…"
                value={courseQuery} onChange={(e) => setCourseQuery(e.target.value)} />
            </div>
          </div>
          <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
            <table>
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Current Faculty</th>
                  <th>Reassign Faculty</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filteredCourses.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.code}</strong>
                      <div className="td-muted">{c.title}</div>
                    </td>
                    <td className="td-muted">{c.faculty_name || <span style={{ color: "var(--text-faint)" }}>Unassigned</span>}</td>
                    <td>
                      <select value={assignments[c.id] ?? ""} onChange={(e) => onFacultyChange(c.id, e.target.value)}
                        style={{ maxWidth: 220 }}>
                        <option value="">Unassigned</option>
                        {facultyUsers.map((f) => <option key={f.id} value={f.id}>{f.full_name}</option>)}
                      </select>
                    </td>
                    <td>
                      <button type="button" className="btn-save" onClick={() => saveAllocation(c.id)}>Save</button>
                    </td>
                  </tr>
                ))}
                {filteredCourses.length === 0 && (
                  <tr><td colSpan={4} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No courses found.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {message.text && <div className="panel-body"><div className={alertClass[message.type] || "alert alert-info"}>{message.text}</div></div>}
        </div>
      )}

      {activeSection === "enrollments" && (
        <div className="panel">
          <div className="panel-header">
            <div>
              <h3>Enroll a Student</h3>
              <p>Assign a student to a course</p>
            </div>
          </div>
          <div className="panel-body">
            <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr auto" }}>
              <div className="form-group">
                <label>Student</label>
                <select value={newEnrollment.student} onChange={(e) => setNewEnrollment((p) => ({ ...p, student: e.target.value }))}>
                  <option value="">Select Student</option>
                  {students.map((s) => <option key={s.id} value={s.id}>{s.full_name} ({s.email})</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Course</label>
                <select value={newEnrollment.course} onChange={(e) => setNewEnrollment((p) => ({ ...p, course: e.target.value }))}>
                  <option value="">Select Course</option>
                  {courses.map((c) => <option key={c.id} value={c.id}>{c.code} – {c.title}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ justifyContent: "flex-end" }}>
                <label>&nbsp;</label>
                <button type="button" className="btn-primary" onClick={createEnrollment}>Enroll</button>
              </div>
            </div>
          </div>

          <div className="panel-header" style={{ borderTop: "1px solid var(--border)" }}>
            <h3>Current Enrollments</h3>
            <span className="badge badge-gray">{enrollments.length} total</span>
          </div>
          <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
            <table>
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Course</th>
                  <th>Enrolled At</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {enrollments.map((e) => (
                  <tr key={e.id}>
                    <td>
                      <strong>{e.student_name}</strong>
                      <div className="td-muted">{e.student_email}</div>
                    </td>
                    <td>
                      <span className="badge badge-blue">{e.course_code}</span>
                      <div className="td-muted" style={{ marginTop: 3 }}>{e.course_title}</div>
                    </td>
                    <td className="td-muted">{new Date(e.enrolled_at).toLocaleString()}</td>
                    <td>
                      <button type="button" className="btn-danger btn-sm" onClick={() => deleteEnrollment(e.id)}>Remove</button>
                    </td>
                  </tr>
                ))}
                {enrollments.length === 0 && (
                  <tr><td colSpan={4} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No enrollments yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {message.text && <div className="panel-body"><div className={alertClass[message.type] || "alert alert-info"}>{message.text}</div></div>}
        </div>
      )}
    </div>
  );
}

/* ─── FACULTY PANEL ─────────────────────────────────────────────── */

function FacultyPanel({ initialSelection, onSelectionConsumed, onBackToTimetable }) {
  const [selectedSession, setSelectedSession] = useState(null);
  const [studentRows, setStudentRows] = useState([]);
  const [qrDurationMinutes, setQrDurationMinutes] = useState(10);
  const [activeQrSession, setActiveQrSession] = useState(null);
  const [qrBusy, setQrBusy] = useState(false);
  const [nowMs, setNowMs] = useState(Date.now());
  const [message, setMessage] = useState({ text: "", type: "info" });

  const refreshSessionRoster = async (sessionInfo, qrSessionInfo = activeQrSession) => {
    if (!sessionInfo?.id) return;

    const [enrollmentRes, attendanceRes] = await Promise.all([
      client.get("/academics/enrollments/"),
      client.get(`/attendance/records/?class_session=${sessionInfo.id}`),
    ]);

    const courseEnrollments = enrollmentRes.data.filter((e) => String(e.course) === String(sessionInfo.course));
    const attendanceMap = new Map(attendanceRes.data.map((r) => [String(r.student), r.status]));

    const mapped = courseEnrollments.map((e) => ({
      student_id: e.student,
      student_name: e.student_name,
      student_email: e.student_email,
      status: attendanceMap.get(String(e.student)) || "absent",
    }));

    setStudentRows(mapped);

    if (qrSessionInfo?.id) {
      const qrRes = await client.get(`/attendance/qr-sessions/${qrSessionInfo.id}/`);
      setActiveQrSession((prev) => ({
        ...(prev || {}),
        ...qrRes.data,
        qr_image: qrRes.data.qr_image || qrSessionInfo.qr_image || prev?.qr_image,
      }));
    }
  };

  const updateStudentStatus = (studentId, status) => {
    setStudentRows((prev) => prev.map((row) => (
      row.student_id === studentId ? { ...row, status } : row
    )));
  };

  const saveManualAttendance = async () => {
    if (!selectedSession?.id) {
      setMessage({ text: "Open a class from timetable first.", type: "warning" });
      return;
    }

    try {
      await client.post("/attendance/records/mark-bulk/", {
        course_id: Number(selectedSession.course),
        class_session_id: Number(selectedSession.id),
        date: selectedSession.date,
        records: studentRows.map((row) => ({
          student_id: row.student_id,
          status: row.status,
          remark: "Manually updated by faculty",
        })),
      });
      await refreshSessionRoster(selectedSession);
      setMessage({ text: "Manual attendance updates saved.", type: "success" });
    } catch (err) {
      setMessage({ text: err?.response?.data?.detail || "Could not save manual attendance.", type: "warning" });
    }
  };

  useEffect(() => {
    if (!initialSelection) return;

    const load = async () => {
      if (!initialSelection.classSessionId) return;
      const sessionRes = await client.get(`/academics/class-sessions/${initialSelection.classSessionId}/`);
      setSelectedSession(sessionRes.data);
      setActiveQrSession(null);
      await refreshSessionRoster(sessionRes.data, null);
      setMessage({ text: "Class loaded. Generate QR to start live attendance.", type: "info" });
    };

    load();

    if (onSelectionConsumed) {
      onSelectionConsumed();
    }
  }, [initialSelection]);

  useEffect(() => {
    const timer = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!selectedSession?.id || !activeQrSession?.id) return;
    const poll = setInterval(() => {
      refreshSessionRoster(selectedSession);
    }, 3000);
    return () => clearInterval(poll);
  }, [selectedSession, activeQrSession?.id]);

  const generateQrSession = async () => {
    if (!selectedSession?.id) {
      setMessage({ text: "Open a class from timetable first.", type: "warning" });
      return;
    }

    try {
      setQrBusy(true);
      const res = await client.post("/attendance/qr-sessions/", {
        class_session_id: Number(selectedSession.id),
        duration_minutes: Number(qrDurationMinutes),
      });
      setActiveQrSession(res.data);
      await refreshSessionRoster(selectedSession, res.data);
      setMessage({ text: "QR session created. Students are premarked absent and will turn present on scan.", type: "success" });
    } catch (err) {
      setMessage({ text: err?.response?.data?.detail || "Could not generate QR session.", type: "warning" });
    } finally {
      setQrBusy(false);
    }
  };

  const deactivateQrSession = async () => {
    if (!activeQrSession?.id) return;
    try {
      setQrBusy(true);
      await client.post(`/attendance/qr-sessions/${activeQrSession.id}/deactivate/`);
      setActiveQrSession((p) => (p ? { ...p, is_active: false } : p));
      if (selectedSession) {
        await refreshSessionRoster(selectedSession);
      }
      setMessage({ text: "QR session deactivated.", type: "success" });
    } catch (err) {
      setMessage({ text: err?.response?.data?.detail || "Could not deactivate session.", type: "warning" });
    } finally {
      setQrBusy(false);
    }
  };

  const presentCount = studentRows.filter((r) => r.status === "present").length;
  const absentCount = studentRows.filter((r) => r.status === "absent").length;
  const lateCount = studentRows.filter((r) => r.status === "late").length;
  const remainingMs = activeQrSession ? Math.max(0, new Date(activeQrSession.ends_at).getTime() - nowMs) : 0;
  const timerText = activeQrSession
    ? `${Math.floor(remainingMs / 60000)}:${String(Math.floor((remainingMs % 60000) / 1000)).padStart(2, "0")}`
    : "--:--";

  return (
    <div className="grid-gap">
      {/* Stats */}
      <div className="stat-grid">
        <div className="stat-card teal">
          <span className="stat-icon">📚</span>
          <span className="stat-label">Class Session</span>
          <strong className="stat-value">{selectedSession ? `${selectedSession.start_time}` : "-"}</strong>
        </div>
        <div className="stat-card green">
          <span className="stat-icon">✅</span>
          <span className="stat-label">Present</span>
          <strong className="stat-value">{presentCount}</strong>
        </div>
        <div className="stat-card amber">
          <span className="stat-icon">⏰</span>
          <span className="stat-label">QR Timer</span>
          <strong className="stat-value">{timerText}</strong>
        </div>
        <div className="stat-card blue">
          <span className="stat-icon">❌</span>
          <span className="stat-label">Absent</span>
          <strong className="stat-value">{absentCount}</strong>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3>Live Class Attendance</h3>
            {selectedSession && <p>{selectedSession.course_code} — {selectedSession.course_title} | {selectedSession.date} {selectedSession.start_time}-{selectedSession.end_time}</p>}
          </div>
          <button type="button" className="btn-secondary" onClick={onBackToTimetable}>Back to Timetable</button>
        </div>
        {!selectedSession && (
          <div className="panel-body">
            <div className="alert alert-info">Open a class from Timetable to start live attendance.</div>
          </div>
        )}

        {selectedSession && (
          <>

            <div className="panel-header" style={{ borderTop: "1px solid var(--border)" }}>
              <div>
                <h3>Live QR Session</h3>
                <p>Generate QR, students are marked absent by default and become present on scan</p>
              </div>
            </div>
            <div className="panel-body">
              <div className="form-grid" style={{ gridTemplateColumns: "220px auto" }}>
                <div className="form-group">
                  <label>Window (minutes)</label>
                  <input
                    type="number"
                    min="1"
                    max="240"
                    value={qrDurationMinutes}
                    onChange={(e) => setQrDurationMinutes(e.target.value)}
                  />
                </div>
                <div className="form-group" style={{ justifyContent: "flex-end" }}>
                  <label>&nbsp;</label>
                  <div className="flex-row">
                    <button type="button" className="btn-primary" onClick={generateQrSession} disabled={qrBusy}>
                      {qrBusy ? "Generating..." : "Generate QR"}
                    </button>
                    {activeQrSession?.is_active && (
                      <button type="button" className="btn-danger" onClick={deactivateQrSession} disabled={qrBusy}>
                        Deactivate
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {activeQrSession && (
                <div className="qr-session-card">
                  <div>
                    <img className="qr-image" src={activeQrSession.qr_image} alt="Attendance session QR" />
                  </div>
                  <div className="qr-session-meta">
                    <h4>Session Token</h4>
                    <p className="qr-token">{activeQrSession.token}</p>
                    <p>
                      Active from <strong>{new Date(activeQrSession.starts_at).toLocaleTimeString()}</strong> to <strong>{new Date(activeQrSession.ends_at).toLocaleTimeString()}</strong>
                    </p>
                    <p>
                      Status: <span className={`badge ${activeQrSession.is_active ? "badge-green" : "badge-gray"}`}>{activeQrSession.is_active ? "Active" : "Inactive"}</span>
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="panel-header" style={{ borderTop: "1px solid var(--border)" }}>
              <h3>Live Student Status</h3>
              <div className="flex-row">
                <span className="badge badge-green">{presentCount} present</span>
                <span className="badge badge-amber">{lateCount} late</span>
                <span className="badge badge-rose">{absentCount} absent</span>
              </div>
            </div>
            <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Student</th>
                    <th>Email</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {studentRows.map((row, idx) => (
                    <tr key={`${row.student_id}-${idx}`}>
                      <td className="td-muted">{idx + 1}</td>
                      <td><strong>{row.student_name}</strong></td>
                      <td className="td-muted">{row.student_email}</td>
                      <td>
                        <select
                          value={row.status}
                          onChange={(e) => updateStudentStatus(row.student_id, e.target.value)}
                          className={row.status === "present" ? "status-select-present" : row.status === "late" ? "status-select-late" : "status-select-absent"}
                          style={{ maxWidth: 130 }}
                        >
                          <option value="present">Present</option>
                          <option value="absent">Absent</option>
                          <option value="late">Late</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                  {studentRows.length === 0 && (
                    <tr><td colSpan={4} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No enrolled students found for this class.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {studentRows.length > 0 && (
              <div className="panel-body" style={{ borderTop: "1px solid var(--border)" }}>
                <button type="button" className="btn-primary" onClick={saveManualAttendance}>
                  Save Manual Attendance
                </button>
              </div>
            )}
          </>
        )}

        {message.text && (
          <div className="panel-body" style={{ borderTop: "1px solid var(--border)" }}>
            <div className={`alert alert-${message.type}`}>{message.text}</div>
          </div>
        )}
      </div>
    </div>
  );
}

function FacultyTimetablePanel({ onOpenAttendance }) {
  const toLocalDateInputValue = (date) => {
    const offsetMs = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offsetMs).toISOString().split("T")[0];
  };

  const countMatchingDays = (startDateStr, endDateStr, weekdays) => {
    if (!startDateStr || !endDateStr || !Array.isArray(weekdays) || weekdays.length === 0) return 0;

    const start = new Date(`${startDateStr}T00:00:00`);
    const end = new Date(`${endDateStr}T00:00:00`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return 0;

    let current = new Date(start);
    let matched = 0;
    while (current <= end) {
      const jsDay = current.getDay();
      const pythonDay = (jsDay + 6) % 7;
      if (weekdays.includes(pythonDay)) matched += 1;
      current.setDate(current.getDate() + 1);
    }
    return matched;
  };

  const today = new Date();
  const monthAhead = new Date();
  monthAhead.setDate(monthAhead.getDate() + 30);

  const [courses, setCourses] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [hideUnscheduled, setHideUnscheduled] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "info" });

  const [autoForm, setAutoForm] = useState({
    course_id: "",
    start_date: toLocalDateInputValue(today),
    end_date: toLocalDateInputValue(monthAhead),
    weekdays: [0, 1, 2, 3, 4],
    start_time: "09:00",
    end_time: "10:00",
    replace_existing: false,
  });

  const [extraForm, setExtraForm] = useState({
    course: "",
    date: new Date().toISOString().split("T")[0],
    start_time: "10:00",
    end_time: "11:00",
    note: "",
  });

  const weekdayChoices = [
    { value: 0, label: "Mon" },
    { value: 1, label: "Tue" },
    { value: 2, label: "Wed" },
    { value: 3, label: "Thu" },
    { value: 4, label: "Fri" },
    { value: 5, label: "Sat" },
    { value: 6, label: "Sun" },
  ];

  const loadData = async () => {
    const [courseRes, sessionRes] = await Promise.all([
      client.get("/academics/courses/"),
      client.get("/academics/class-sessions/"),
    ]);

    setCourses(courseRes.data);
    setSessions(sessionRes.data);

    if (courseRes.data.length > 0) {
      const first = String(courseRes.data[0].id);
      setAutoForm((p) => ({ ...p, course_id: p.course_id || first }));
      setExtraForm((p) => ({ ...p, course: p.course || first }));
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleWeekday = (day) => {
    setAutoForm((p) => {
      const exists = p.weekdays.includes(day);
      const next = exists ? p.weekdays.filter((d) => d !== day) : [...p.weekdays, day];
      return { ...p, weekdays: next.sort((a, b) => a - b) };
    });
  };

  const submitAutoSchedule = async () => {
    if (!autoForm.course_id || autoForm.weekdays.length === 0) {
      setMessage({ text: "Select a course and at least one weekday.", type: "warning" });
      return;
    }

    const matchedDays = countMatchingDays(autoForm.start_date, autoForm.end_date, autoForm.weekdays);
    if (matchedDays === 0) {
      setMessage({
        text: "No selected weekday falls inside this date range. Adjust date range or weekday chips.",
        type: "warning",
      });
      return;
    }

    try {
      const payload = {
        ...autoForm,
        course_id: Number(autoForm.course_id),
      };
      const res = await client.post("/academics/class-sessions/auto-schedule/", payload);
      const created = Number(res.data.created || 0);
      const updated = Number(res.data.updated || 0);
      const skipped = Number(res.data.skipped || 0);
      if (created + updated === 0) {
        setMessage({
          text: `No classes were scheduled. ${matchedDays} matching day(s) were checked and ${skipped} slot(s) were skipped. Enable Replace Existing if needed.`,
          type: "warning",
        });
      } else {
        setMessage({ text: `Auto schedule complete: ${created} created, ${updated} updated, ${skipped} skipped.`, type: "success" });
      }
      await loadData();
    } catch (err) {
      setMessage({ text: err?.response?.data?.detail || "Could not auto schedule classes.", type: "warning" });
    }
  };

  const submitExtraClass = async () => {
    if (!extraForm.course || !extraForm.date || !extraForm.start_time || !extraForm.end_time) {
      setMessage({ text: "Fill all required fields for extra class.", type: "warning" });
      return;
    }

    try {
      await client.post("/academics/class-sessions/", {
        course: Number(extraForm.course),
        date: extraForm.date,
        start_time: extraForm.start_time,
        end_time: extraForm.end_time,
        session_type: "extra",
        note: extraForm.note,
      });
      setMessage({ text: "Extra class scheduled.", type: "success" });
      setExtraForm((p) => ({ ...p, note: "" }));
      await loadData();
    } catch (err) {
      setMessage({ text: err?.response?.data?.detail || "Could not schedule extra class.", type: "warning" });
    }
  };

  const unscheduleClass = async (sessionId) => {
    try {
      await client.post(`/academics/class-sessions/${sessionId}/unschedule/`, {});
      setMessage({ text: "Class unscheduled.", type: "success" });
      await loadData();
    } catch (err) {
      setMessage({ text: err?.response?.data?.detail || "Could not unschedule class.", type: "warning" });
    }
  };

  const visibleSessions = hideUnscheduled
    ? sessions.filter((s) => s.status !== "cancelled")
    : sessions;

  return (
    <div className="grid-gap">
      {message.text && <div className={`alert alert-${message.type}`}>{message.text}</div>}

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3>Auto Schedule Recurring Classes</h3>
            <p>Create regular sessions across a date range</p>
          </div>
        </div>
        <div className="panel-body">
          <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
            <div className="form-group">
              <label>Course</label>
              <select value={autoForm.course_id} onChange={(e) => setAutoForm((p) => ({ ...p, course_id: e.target.value }))}>
                <option value="">Select Course</option>
                {courses.map((c) => <option key={c.id} value={c.id}>{c.code} - {c.title}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Start Date</label>
              <input type="date" value={autoForm.start_date} onChange={(e) => setAutoForm((p) => ({ ...p, start_date: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>End Date</label>
              <input type="date" value={autoForm.end_date} onChange={(e) => setAutoForm((p) => ({ ...p, end_date: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Start Time</label>
              <input type="time" value={autoForm.start_time} onChange={(e) => setAutoForm((p) => ({ ...p, start_time: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>End Time</label>
              <input type="time" value={autoForm.end_time} onChange={(e) => setAutoForm((p) => ({ ...p, end_time: e.target.value }))} />
            </div>
            <div className="form-group" style={{ justifyContent: "flex-end" }}>
              <label>&nbsp;</label>
              <button type="button" className="btn-primary" onClick={submitAutoSchedule}>Auto Schedule</button>
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <label style={{ display: "block", fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>Repeat On</label>
            <div className="flex-row">
              {weekdayChoices.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  className={autoForm.weekdays.includes(d.value) ? "btn-chip active" : "btn-chip"}
                  onClick={() => toggleWeekday(d.value)}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-muted)" }}>
              <input
                type="checkbox"
                checked={autoForm.replace_existing}
                onChange={(e) => setAutoForm((p) => ({ ...p, replace_existing: e.target.checked }))}
              />
              Replace existing sessions at same date and start time
            </label>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <div>
            <h3>Schedule Extra Class</h3>
            <p>Add one-off manual classes outside regular schedule</p>
          </div>
        </div>
        <div className="panel-body">
          <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr" }}>
            <div className="form-group">
              <label>Course</label>
              <select value={extraForm.course} onChange={(e) => setExtraForm((p) => ({ ...p, course: e.target.value }))}>
                <option value="">Select Course</option>
                {courses.map((c) => <option key={c.id} value={c.id}>{c.code} - {c.title}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Date</label>
              <input type="date" value={extraForm.date} onChange={(e) => setExtraForm((p) => ({ ...p, date: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Start Time</label>
              <input type="time" value={extraForm.start_time} onChange={(e) => setExtraForm((p) => ({ ...p, start_time: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>End Time</label>
              <input type="time" value={extraForm.end_time} onChange={(e) => setExtraForm((p) => ({ ...p, end_time: e.target.value }))} />
            </div>
          </div>
          <div className="form-group" style={{ marginTop: 10 }}>
            <label>Note (optional)</label>
            <input type="text" value={extraForm.note} onChange={(e) => setExtraForm((p) => ({ ...p, note: e.target.value }))} placeholder="e.g. Revision class" />
          </div>
          <div style={{ marginTop: 14 }}>
            <button type="button" className="btn-secondary" onClick={submitExtraClass}>Add Extra Class</button>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Scheduled Classes</h3>
          <div className="flex-row">
            <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-muted)" }}>
              <input
                type="checkbox"
                checked={hideUnscheduled}
                onChange={(e) => setHideUnscheduled(e.target.checked)}
              />
              Hide unscheduled classes
            </label>
            <span className="badge badge-gray">{visibleSessions.length} shown</span>
          </div>
        </div>
        <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Course</th>
                <th>Time</th>
                <th>Type</th>
                <th>Status</th>
                <th>Note</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visibleSessions.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => {
                    if (s.status === "cancelled") return;
                    if (onOpenAttendance) {
                      onOpenAttendance({
                        courseId: s.course,
                        classSessionId: s.id,
                        date: s.date,
                      });
                    }
                  }}
                  style={{ cursor: s.status === "cancelled" ? "default" : "pointer" }}
                >
                  <td className="td-muted">{s.date}</td>
                  <td>
                    <strong>{s.course_code}</strong>
                    <div className="td-muted">{s.course_title}</div>
                  </td>
                  <td className="td-muted">{s.start_time} - {s.end_time}</td>
                  <td>
                    <span className={`badge ${s.session_type === "extra" ? "badge-amber" : "badge-blue"}`} style={{ textTransform: "capitalize" }}>
                      {s.session_type}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${s.status === "scheduled" ? "badge-green" : s.status === "completed" ? "badge-blue" : "badge-rose"}`} style={{ textTransform: "capitalize" }}>
                      {s.status}
                    </span>
                  </td>
                  <td className="td-muted">{s.note || "-"}</td>
                  <td>
                    {s.status === "scheduled" ? (
                      <button
                        type="button"
                        className="btn-danger btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          unscheduleClass(s.id);
                        }}
                      >
                        Unschedule
                      </button>
                    ) : (
                      <span className="td-muted">-</span>
                    )}
                  </td>
                </tr>
              ))}
              {visibleSessions.length === 0 && (
                <tr><td colSpan={7} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No class sessions scheduled yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─── STUDENT PANEL ─────────────────────────────────────────────── */

function StudentPanel({ activeSection }) {
  const [records, setRecords] = useState([]);
  const [scanToken, setScanToken] = useState("");
  const [scanBusy, setScanBusy] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "info" });

  useEffect(() => {
    client.get("/attendance/records/").then((res) => setRecords(res.data));
  }, []);

  const refreshRecords = async () => {
    const res = await client.get("/attendance/records/");
    setRecords(res.data);
  };

  const summary = useMemo(() => {
    const total = records.length;
    const present = records.filter((r) => r.status === "present").length;
    return { total, present, pct: total ? Math.round((present / total) * 100) : 0 };
  }, [records]);

  const courseWise = useMemo(() => {
    const byCourse = {};
    records.forEach((r) => {
      if (!byCourse[r.course]) {
        byCourse[r.course] = {
          course: r.course,
          courseCode: r.course_code || `Course ${r.course}`,
          courseTitle: r.course_title || "",
          total: 0, present: 0,
        };
      }
      byCourse[r.course].total += 1;
      if (r.status === "present") byCourse[r.course].present += 1;
    });
    return Object.values(byCourse).map((item) => ({
      ...item,
      percentage: item.total ? Math.round((item.present / item.total) * 100) : 0,
    }));
  }, [records]);

  const pctColor = (pct) => pct >= 75 ? "green" : pct >= 50 ? "amber" : "rose";

  if (activeSection === "overview") {
    return (
      <div className="grid-gap">
        {message.text && (
          <div className={`alert alert-${message.type}`}>{message.text}</div>
        )}

        
        {/* Summary stats */}
        <div className="stat-grid">
          <div className="stat-card blue">
            <span className="stat-icon">📅</span>
            <span className="stat-label">Total Classes</span>
            <strong className="stat-value">{summary.total}</strong>
          </div>
          <div className="stat-card green">
            <span className="stat-icon">✅</span>
            <span className="stat-label">Present</span>
            <strong className="stat-value">{summary.present}</strong>
          </div>
          <div className="stat-card amber">
            <span className="stat-icon">📊</span>
            <span className="stat-label">Attendance</span>
            <strong className="stat-value">{summary.pct}%</strong>
          </div>
        </div>

        {/* Overall progress */}
        <div className="panel">
          <div className="panel-header">
            <h3>Overall Attendance</h3>
            <span className={`badge badge-${summary.pct >= 75 ? "green" : summary.pct >= 50 ? "amber" : "rose"}`}>
              {summary.pct}%
            </span>
          </div>
          <div className="panel-body">
            <div className="progress-track" style={{ height: 12 }}>
              <div className={`progress-fill ${pctColor(summary.pct)}`} style={{ width: `${summary.pct}%` }} />
            </div>
            <p style={{ marginTop: 8, fontSize: 13, color: "var(--text-muted)" }}>
              {summary.present} out of {summary.total} classes attended
            </p>
          </div>
        </div>

        {/* Course-wise */}
        <div className="panel">
          <div className="panel-header">
            <h3>Course-wise Breakdown</h3>
          </div>
          <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
            <table>
              <thead>
                <tr>
                  <th>Course</th>
                  <th>Present</th>
                  <th>Total</th>
                  <th>Progress</th>
                  <th>%</th>
                </tr>
              </thead>
              <tbody>
                {courseWise.map((item) => (
                  <tr key={item.course}>
                    <td>
                      <strong>{item.courseCode}</strong>
                      {item.courseTitle && <div className="td-muted">{item.courseTitle}</div>}
                    </td>
                    <td>{item.present}</td>
                    <td>{item.total}</td>
                    <td style={{ minWidth: 120 }}>
                      <div className="progress-track compact">
                        <div className={`progress-fill ${pctColor(item.percentage)}`} style={{ width: `${item.percentage}%` }} />
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-${item.percentage >= 75 ? "green" : item.percentage >= 50 ? "amber" : "rose"}`}>
                        {item.percentage}%
                      </span>
                    </td>
                  </tr>
                ))}
                {courseWise.length === 0 && (
                  <tr><td colSpan={5} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No records yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  }

  // history section
  return (
    <div className="grid-gap">
      {message.text && (
        <div className={`alert alert-${message.type}`}>{message.text}</div>
      )}
      <div className="panel">
        <div className="panel-header">
          <h3>Full Attendance Log</h3>
          <span className="badge badge-gray">{records.length} records</span>
        </div>
        <div className="table-wrap" style={{ borderRadius: 0, border: "none", borderTop: "1px solid var(--border)" }}>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Course</th>
                <th>Status</th>
                <th>Remark</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <tr key={r.id}>
                  <td className="td-muted">{r.date}</td>
                  <td>
                    {r.course_code
                      ? <><strong>{r.course_code}</strong><div className="td-muted">{r.course_title}</div></>
                      : r.course}
                  </td>
                  <td>
                    <span className={`badge badge-${r.status === "present" ? "green" : r.status === "late" ? "amber" : "rose"}`}
                      style={{ textTransform: "capitalize" }}>
                      {r.status}
                    </span>
                  </td>
                  <td className="td-muted">{r.remark || "—"}</td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr><td colSpan={4} style={{ color: "var(--text-muted)", textAlign: "center", padding: "24px" }}>No attendance data available.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ─── DASHBOARD PAGE (ROOT) ─────────────────────────────────────── */

export default function DashboardPage() {
  const { user, logout } = useAuth();

  const defaultNav = useMemo(() => {
    if (user.role === "admin") return "users";
    if (user.role === "faculty") return "timetable";
    return "overview";
  }, [user.role]);

  const [activeNav, setActiveNav] = useState(defaultNav);
  const [facultyAttendanceSelection, setFacultyAttendanceSelection] = useState(null);

  const openFacultyAttendanceFromSession = (selection) => {
    setFacultyAttendanceSelection(selection);
    setActiveNav("attendance");
  };

  return (
    <AppShell user={user} logout={logout} activeNav={activeNav} setActiveNav={setActiveNav}>
      {user.role === "admin" && <AdminPanel activeSection={activeNav} />}
      {user.role === "faculty" && activeNav === "attendance" && (
        <FacultyPanel
          initialSelection={facultyAttendanceSelection}
          onSelectionConsumed={() => setFacultyAttendanceSelection(null)}
          onBackToTimetable={() => setActiveNav("timetable")}
        />
      )}
      {user.role === "faculty" && activeNav === "timetable" && (
        <FacultyTimetablePanel onOpenAttendance={openFacultyAttendanceFromSession} />
      )}
      {user.role === "student" && <StudentPanel activeSection={activeNav} />}
    </AppShell>
  );
}
