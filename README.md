# University Management System (Django + React + MySQL)

This is the initial MVP scaffold based on your selected features:
- Role-based auth (admin/faculty/student)
- Profile-aware dashboard
- Academic setup models (department, semester, course, enrollment)
- Faculty attendance marking (bulk)
- Student attendance viewing

## Project Structure
- `backend/` Django REST API
- `frontend/` React app (Vite)
- `features.md` feature checklist

## Backend Setup
1. Go to backend:
   - `cd backend`
2. Create and activate virtual environment:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Create `.env` from `.env.example` and update MySQL credentials.
5. If your local MariaDB user cannot create new DBs, use an existing writable DB (example used in this setup: `test`).
6. For local socket-based MariaDB setups, use:
   - `MYSQL_HOST=localhost`
   - `MYSQL_PORT=`
   - `MYSQL_DB=test` (or your writable DB)
   - `MYSQL_USER=<your_user>`
   - `MYSQL_PASSWORD=<your_password_or_empty>`
6. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
7. Create admin user:
   - `python manage.py createsuperuser`
8. Run backend:
   - `python manage.py runserver`
   - or, for access from a phone or emulator on the same network, set `DJANGO_RUNSERVER_ADDR=0.0.0.0:8000` and include your laptop's hotspot IP in `DJANGO_ALLOWED_HOSTS`

Backend URL: `http://127.0.0.1:8000`

## Frontend Setup
1. Go to frontend:
   - `cd frontend`
2. Install dependencies:
   - `npm install`
3. Run frontend:
   - `npm run dev`

Frontend URL: `http://127.0.0.1:5173`

## Seeded Demo Data (Current Local Setup)
These demo users were seeded and verified:
- Admin: `admin@ums.local` / `Admin@12345`
- Faculty: `faculty@ums.local` / `Faculty@12345`
- Student: `student@ums.local` / `Student@12345`

Seeded sample academic data:
- Department: `CSE`
- Semester: `Spring 2026`
- Course: `CSE101 - Intro to Programming`
- Enrollment: student enrolled in `CSE101`
- Attendance records: 3 entries for the sample student

## Live Verification Completed
The following checks passed on this machine:
- Frontend reachable at `http://127.0.0.1:5173/` (HTTP 200)
- Admin, faculty, and student login via JWT
- Faculty bulk attendance marking endpoint
- Student attendance listing endpoint

## API Endpoints (MVP)
### Auth
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `GET /api/auth/users/` (admin)
- `POST /api/auth/register/` (admin)

### Academics
- `GET/POST /api/academics/departments/` (admin)
- `GET/POST /api/academics/semesters/` (admin)
- `GET/POST /api/academics/courses/` (admin)
- `GET/POST /api/academics/enrollments/` (admin/faculty scoped)

### Attendance
- `GET/POST /api/attendance/records/`
- `POST /api/attendance/records/mark-bulk/`

## What to Build Next
1. Admin UI for managing departments, semesters, courses, and enrollments
2. Faculty timetable and course filters
3. Student profile and academic detail pages
4. Better attendance reports by subject
