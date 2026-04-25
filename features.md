# University Management System Features

Use this as a working checklist. Add/remove items before implementation.

## 1. Core Platform
- [ ] Role-based auth (Admin, Faculty, Student)
- [ ] Secure login/logout
- [ ] Dashboard per role
- [ ] Profile management for all users
- [ ] Mobile-responsive UI

## 2. Admin Panel
### User & Access
- [ ] Manage users (create, edit, deactivate)
- [ ] Assign roles and permissions

### Academic Setup
- [ ] Departments, programs, batches, sections
- [ ] Semester/session management
- [ ] Course catalog and credit structure
- [ ] Subject-faculty mapping

### Admissions
- [ ] New student enrollment

### Attendance & Exams
- [ ] basic ability for faculty to mark attendance for a list of students
- [ ] student should be able to view their attendance


## 3. Faculty Panel
- [ ] View teaching timetable
- [ ] View assigned courses/sections
- [ ] Mark and update attendance
- [ ] Upload lecture materials
- [ ] Evaluate submissions and publish marks

## 4. Student Panel
- [ ] View profile and academic details
- [ ] Course registration (if applicable)
- [ ] View attendance by subject

- [ ] Mobile app API readiness

## 6. Technical/Non-Functional Requirements
- [ ] Backend: Django + Django REST Framework
- [ ] Frontend: React
- [ ] Database: MySQL
- [ ] JWT/session authentication strategy finalized
- [ ] Role-based API authorization implemented
- [ ] Logging and monitoring
- [ ] Backup and restore strategy

## 7. MVP Scope (Recommended First Build)
- [ ] Authentication + role management
- [ ] Student/faculty/admin profile management
- [ ] Department/course/semester setup
- [ ] Timetable management
- [ ] Attendance management

## Notes
- Keep this document updated before each sprint.
- Move out-of-scope items into Optional Modules.
